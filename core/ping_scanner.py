"""
Ping Scanner module for the Serial Monitor application.
Provides functionality to scan IP ranges and detect hosts and open ports.
"""
import sys
import socket
import subprocess
import concurrent.futures
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Set
import ipaddress
from PyQt6.QtCore import QThread, pyqtSignal

from utils.network_utils import ping_host, get_hostname, scan_ports


class PingWorker(QThread):
    result_ready = pyqtSignal(str, bool, float, str)
    
    def __init__(self, ip: str, timeout_ms: int, dns_enabled: bool = False, port_scan: Optional[Tuple[int, int]] = None):
        super().__init__()
        self.ip = ip
        self.timeout_ms = timeout_ms
        self.dns_enabled = dns_enabled
        self.port_scan = port_scan
        
    def run(self):
        try:
            # Determine if on local network for optimization
            is_local = self._is_local_network(self.ip)
            
            # Try multiple detection methods
            success, response_time = self._detect_host(is_local)
            
            # DNS Resolution if enabled and host is up
            dns_name = "N/A"
            if success and self.dns_enabled:
                try:
                    if self.ip == '127.0.0.1':
                        dns_name = 'localhost'
                    else:
                        dns_name = socket.gethostbyaddr(self.ip)[0]
                except (socket.herror, socket.gaierror):
                    pass
            
            # Port scanning if requested and host is up
            if success and self.port_scan:
                open_ports = self.scan_ports(*self.port_scan)
                if open_ports:
                    # Group ports by common services
                    service_info = self._identify_services(open_ports)
                    dns_name = service_info
                else:
                    dns_name = "No open ports found"
                    
            self.result_ready.emit(self.ip, success, response_time, dns_name)
            
        except Exception as e:
            self.result_ready.emit(self.ip, False, 0, f"Error: {str(e)}")
    
    def _is_local_network(self, ip: str) -> bool:
        """Check if IP is on local network for optimization"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            
            # Check for common local networks
            if ip_obj.is_private:
                return True
            if ip_obj.is_loopback:
                return True
                
            # Check if IP is on same subnet as local machine
            my_ip = self._get_local_ip()
            if my_ip:
                my_network = ipaddress.ip_network(f"{my_ip}/24", strict=False)
                return ip_obj in my_network
                
            return False
        except:
            return False
    
    def _get_local_ip(self) -> Optional[str]:
        """Get the local IP address of this machine"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Doesn't need to be reachable
            s.connect(('10.255.255.255', 1))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return None
            
    def _detect_host(self, is_local: bool) -> Tuple[bool, float]:
        """Try multiple methods to detect if host is up"""
        
        # Method 1: Check if it's localhost or this machine
        if self.ip in ('127.0.0.1', 'localhost', socket.gethostname()):
            return True, 0.1  # Nominal value for localhost
        
        # Start timing
        start_time = datetime.now()
        
        # Method 2: ICMP Ping (more packets for reliability)
        ping_success = self._icmp_ping()
        if ping_success:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            return True, response_time
            
        # Method 3: TCP Ping to common ports for hosts that block ICMP
        if not is_local:  # Skip for local network to avoid timeouts
            tcp_success = self._tcp_ping()
            if tcp_success:
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                return True, response_time
        
        # If we get here, host is down
        return False, self.timeout_ms
    
    def _icmp_ping(self) -> bool:
        """Perform ICMP ping with multiple packets for reliability"""
        timeout_sec = self.timeout_ms / 1000
        
        # Send multiple pings to improve reliability
        num_pings = 2  # Try 2 pings to reduce false negatives
        
        if sys.platform == "win32":
            ping_cmd = ['ping', '-n', str(num_pings), '-w', str(self.timeout_ms), '-4', self.ip]
            
            # Create startupinfo to hide console window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            
            try:
                process = subprocess.run(
                    ping_cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=timeout_sec * num_pings + 1,
                    startupinfo=startupinfo
                )
                return process.returncode == 0
            except Exception:
                return False
        else:
            # Non-Windows platforms
            ping_cmd = ['ping', '-c', str(num_pings), '-W', str(int(timeout_sec)), self.ip]
            
            try:
                process = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=timeout_sec * num_pings + 1)
                return process.returncode == 0
            except Exception:
                return False
        
    def _tcp_ping(self) -> bool:
        """Try TCP connections to common ports that are often open"""
        common_ports = [80, 443, 22, 3389]  # HTTP, HTTPS, SSH, RDP
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout_ms / 1000 / 2)  # Half the ping timeout in seconds
                result = sock.connect_ex((self.ip, port))
                sock.close()
                
                if result == 0:
                    return True  # Connection successful, host is up
            except:
                pass
        
        return False
            
    def scan_ports(self, start_port: int, end_port: int) -> List[int]:
        """Scan ports in parallel for better performance"""
        open_ports = []
        
        # Determine how many ports to scan
        ports_to_scan = range(start_port, end_port + 1)
        
        # For small port ranges, scan sequentially
        if end_port - start_port < 50:
            for port in ports_to_scan:
                if self._is_port_open(port):
                    open_ports.append(port)
        else:
            # For larger ranges, use parallel scanning
            # Use min(100, os.cpu_count() * 5) workers in a real implementation
            max_workers = min(50, len(ports_to_scan))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all port checks to the executor
                future_to_port = {
                    executor.submit(self._is_port_open, port): port 
                    for port in ports_to_scan
                }
                
                # Process results as they complete
                for future in concurrent.futures.as_completed(future_to_port):
                    port = future_to_port[future]
                    try:
                        is_open = future.result()
                        if is_open:
                            open_ports.append(port)
                    except Exception:
                        # Skip ports that cause errors
                        pass
                        
        # Sort the open ports for display
        open_ports.sort()
        return open_ports
    
    def _is_port_open(self, port: int) -> bool:
        """Check if a single port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout_ms / 1000 / 4)  # Quarter of the ping timeout
            result = sock.connect_ex((self.ip, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def _identify_services(self, open_ports: List[int]) -> str:
        """Identify common services on open ports"""
        common_services = {
            20: 'FTP-Data', 21: 'FTP', 22: 'SSH', 23: 'Telnet',
            25: 'SMTP', 53: 'DNS', 80: 'HTTP', 110: 'POP3',
            123: 'NTP', 143: 'IMAP', 443: 'HTTPS', 465: 'SMTPS',
            587: 'SMTP+TLS', 993: 'IMAPS', 995: 'POP3S',
            3306: 'MySQL', 3389: 'RDP', 5432: 'PostgreSQL',
            8080: 'HTTP-Alt', 8443: 'HTTPS-Alt'
        }
        
        # Group ports by service if known
        service_ports = []
        unknown_ports = []
        
        for port in open_ports:
            if port in common_services:
                service_ports.append(f"{port}({common_services[port]})")
            else:
                unknown_ports.append(str(port))
        
        # Combine results
        result_parts = []
        
        if service_ports:
            result_parts.append("Services: " + ", ".join(service_ports))
        
        if unknown_ports:
            if len(unknown_ports) <= 5:
                result_parts.append("Other ports: " + ", ".join(unknown_ports))
            else:
                result_parts.append(f"Other ports: {len(unknown_ports)} ports open")
        
        return " | ".join(result_parts)


# Constants
DEFAULT_TIMEOUT_MS = 1000
MAX_CONCURRENT_THREADS = 50
BATCH_UPDATE_SIZE = 10

# Common ports for scanning with better organization
COMMON_PORTS = {
    "Web Services (80, 443, 8080)": (80, 8080),
    "Email Services (25, 110, 143, 465, 587, 993)": (25, 993),
    "File Services (20-22, 445, 3389)": (20, 3389),
    "Database Services (1433, 3306, 5432, 6379, 27017)": (1433, 27017),
    "Common Ports (1-1024)": (1, 1024),
    "Extended Scan (1-10000)": (1, 10000),
    "Full Scan (1-65535)": (1, 65535)
}

def get_ip_range(start_ip: str, end_ip: str) -> List[str]:
    """Generate list of IPs between start and end IP with improved efficiency"""
    try:
        # Handle single IP case
        if not end_ip:
            return [start_ip.strip()]
        
        # Handle CIDR notation if provided
        if '/' in start_ip and not end_ip:
            network = ipaddress.ip_network(start_ip.strip(), strict=False)
            # For small networks, return all IPs
            if network.num_addresses <= 1024:
                return [str(ip) for ip in network.hosts()]
            else:
                raise ValueError(f"Network too large: {network.num_addresses} addresses")
            
        # Handle start-end range    
        start = ipaddress.ip_address(start_ip.strip())
        end = ipaddress.ip_address(end_ip.strip())
        
        if start.version != end.version:
            raise ValueError("IP versions don't match")
        if start > end:
            raise ValueError("Start IP must be less than or equal to End IP")
        
        # For single IP
        if start == end:
            return [str(start)]
            
        # For small ranges, generate directly
        if int(end) - int(start) <= 1024:
            return [str(ipaddress.ip_address(i)) 
                   for i in range(int(start), int(end) + 1)]
        
        # For larger ranges, use summarize_address_range (more efficient)
        ips = []
        networks = ipaddress.summarize_address_range(start, end)
        for network in networks:
            # Add IPs from each network
            if network.num_addresses <= 1024:
                ips.extend([str(ip) for ip in network.hosts()])
            else:
                # For very large networks, take sample IPs 
                # This approach limits the total IPs to prevent memory issues
                ips.extend([str(network[i]) for i in range(0, network.num_addresses, 
                            max(1, network.num_addresses // 1024))])
        
        return ips
        
    except Exception as e:
        raise ValueError(f"Invalid IP range: {str(e)}")