"""
Enhanced Ping Scanner module with improved port scanning capabilities.
Designed for Windows 10 without requiring administrator privileges.
Production-ready version with comprehensive fixes and improvements.
"""
import sys
import socket
import subprocess
import concurrent.futures
import threading
import time
import struct
import random
import queue
import weakref
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Set, Any
import ipaddress
from collections import defaultdict
from contextlib import contextmanager
from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

# Constants for Windows subprocess
if sys.platform == 'win32':
    CREATE_NO_WINDOW = 0x08000000
    SW_HIDE = 0
else:
    CREATE_NO_WINDOW = 0
    SW_HIDE = None

# Service identification signatures
SERVICE_SIGNATURES = {
    'HTTP': [b'HTTP/', b'<!DOCTYPE', b'<html', b'<HTML'],
    'SSH': [b'SSH-', b'OpenSSH'],
    'FTP': [b'220 ', b'220-'],
    'SMTP': [b'220 ', b'ESMTP'],
    'POP3': [b'+OK'],
    'IMAP': [b'* OK', b'IMAP4'],
    'MySQL': [b'mysql', b'MariaDB'],
    'PostgreSQL': [b'PostgreSQL'],
    'RDP': [b'\x00\x00\x00'],
    'HTTPS': [b'\x16\x03'],  # TLS handshake
    'DNS': [b'\x00\x00\x01\x00'],
    'TELNET': [b'\xff\xfd', b'\xff\xfb'],
}

# Extended port-to-service mapping
COMMON_SERVICES = {
    20: 'FTP-Data', 21: 'FTP', 22: 'SSH', 23: 'Telnet',
    25: 'SMTP', 53: 'DNS', 67: 'DHCP', 68: 'DHCP',
    80: 'HTTP', 110: 'POP3', 111: 'RPC', 123: 'NTP',
    135: 'RPC', 139: 'NetBIOS', 143: 'IMAP', 161: 'SNMP',
    443: 'HTTPS', 445: 'SMB', 465: 'SMTPS', 514: 'Syslog',
    587: 'SMTP', 636: 'LDAPS', 993: 'IMAPS', 995: 'POP3S',
    1433: 'MSSQL', 1521: 'Oracle', 1723: 'PPTP', 2049: 'NFS',
    3306: 'MySQL', 3389: 'RDP', 5432: 'PostgreSQL', 5900: 'VNC',
    5985: 'WinRM', 6379: 'Redis', 8080: 'HTTP-Alt', 8443: 'HTTPS-Alt',
    8888: 'HTTP-Alt', 9000: 'HTTP', 27017: 'MongoDB'
}

# Priority ports for quick scans
PRIORITY_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 
    993, 995, 1433, 1723, 3306, 3389, 5432, 5900, 8080, 8443
]


class PortScanResult:
    """Container for detailed port scan results"""
    def __init__(self, port: int, is_open: bool):
        self.port = port
        self.is_open = is_open
        self.service_name = COMMON_SERVICES.get(port, 'Unknown')
        self.banner = None
        self.service_version = None
        self.response_time = None
        self.scan_method = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'port': self.port,
            'is_open': self.is_open,
            'service': self.service_name,
            'banner': self.banner,
            'version': self.service_version,
            'response_time': self.response_time,
            'method': self.scan_method
        }


class ScanProfile:
    """Predefined scan profiles for different use cases"""
    
    QUICK = {
        'name': 'Quick Scan',
        'timeout_ms': 500,
        'port_timeout_ms': 250,
        'methods': ['icmp', 'tcp_common'],
        'ports': PRIORITY_PORTS,
        'banner_grab': False,
        'parallel_workers': 20
    }
    
    DETAILED = {
        'name': 'Detailed Scan',
        'timeout_ms': 2000,
        'port_timeout_ms': 500,
        'methods': ['icmp', 'tcp', 'udp_common'],
        'ports': 'common_1024',  # Ports 1-1024
        'banner_grab': True,
        'parallel_workers': 50
    }
    
    CUSTOM = {
        'name': 'Custom Scan',
        'timeout_ms': 1000,
        'port_timeout_ms': 300,
        'methods': ['icmp', 'tcp'],
        'ports': None,  # User-defined
        'banner_grab': True,
        'parallel_workers': 30
    }


class SocketManager:
    """Context manager for safe socket handling"""
    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM):
        self.family = family
        self.type = type
        self.socket = None
        
    def __enter__(self):
        self.socket = socket.socket(self.family, self.type)
        return self.socket
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


class ProgressThrottler:
    """Throttle progress updates to prevent UI flooding"""
    def __init__(self, min_interval=0.1):
        self.min_interval = min_interval
        self.last_update = 0
        self.pending_update = None
        self.lock = threading.Lock()
        
    def should_update(self, current, total):
        """Check if we should emit a progress update"""
        now = time.time()
        with self.lock:
            # Always update on completion
            if current >= total:
                return True
                
            # Throttle intermediate updates
            if now - self.last_update >= self.min_interval:
                self.last_update = now
                return True
            else:
                # Store pending update
                self.pending_update = (current, total)
                return False
    
    def get_pending(self):
        """Get any pending update"""
        with self.lock:
            update = self.pending_update
            self.pending_update = None
            return update


class EnhancedPortScanner:
    """Enhanced port scanner with improved accuracy and features"""
    
    def __init__(self, target_ip: str, timeout_ms: int = 300):
        self.target_ip = target_ip
        self.timeout_ms = timeout_ms
        self.timeout_sec = timeout_ms / 1000.0
        self._socket_lock = threading.Lock()
        
    def scan_port_tcp(self, port: int, grab_banner: bool = False) -> PortScanResult:
        """Enhanced TCP port scan with optional banner grabbing"""
        result = PortScanResult(port, False)
        start_time = time.time()
        
        try:
            with SocketManager() as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(self.timeout_sec)
                
                # Try to connect
                errno = sock.connect_ex((self.target_ip, port))
                
                if errno == 0:
                    result.is_open = True
                    result.response_time = (time.time() - start_time) * 1000
                    result.scan_method = 'TCP_CONNECT'
                    
                    if grab_banner:
                        try:
                            # Send appropriate probe based on port
                            probe = self._get_service_probe(port)
                            if probe:
                                sock.send(probe)
                            
                            # Set shorter timeout for banner grab
                            sock.settimeout(min(1.0, self.timeout_sec))
                            
                            # Try to receive banner
                            banner_data = sock.recv(1024)
                            if banner_data:
                                result.banner = self._safe_decode(banner_data)
                                result.service_name = self._identify_service(banner_data, port)
                                result.service_version = self._extract_version(banner_data)
                        except socket.timeout:
                            pass
                        except Exception:
                            pass
            
        except socket.timeout:
            result.scan_method = 'TCP_TIMEOUT'
        except OSError as e:
            # More specific error handling
            if e.errno == 10061:  # Connection refused
                result.scan_method = 'TCP_REFUSED'
            elif e.errno == 10060:  # Timeout
                result.scan_method = 'TCP_TIMEOUT'
            else:
                result.scan_method = f'TCP_ERROR: {e.errno}'
        except Exception as e:
            result.scan_method = f'TCP_ERROR: {type(e).__name__}'
            
        return result
    
    def scan_port_udp(self, port: int) -> PortScanResult:
        """UDP port scan (limited without admin rights)"""
        result = PortScanResult(port, False)
        
        # Common UDP ports that might respond
        udp_responsive_ports = {53, 123, 161, 500, 514, 1900, 5353}
        
        if port not in udp_responsive_ports:
            result.scan_method = 'UDP_SKIPPED'
            return result
            
        try:
            with SocketManager(type=socket.SOCK_DGRAM) as sock:
                sock.settimeout(self.timeout_sec)
                
                # Send appropriate UDP probe
                probe = self._get_udp_probe(port)
                sock.sendto(probe, (self.target_ip, port))
                
                # Try to receive response
                try:
                    data, addr = sock.recvfrom(1024)
                    if data:
                        result.is_open = True
                        result.banner = self._safe_decode(data)
                        result.scan_method = 'UDP_RESPONSE'
                except socket.timeout:
                    # No response doesn't mean closed for UDP
                    result.scan_method = 'UDP_TIMEOUT'
                    
        except Exception as e:
            result.scan_method = f'UDP_ERROR: {type(e).__name__}'
            
        return result
    
    def _get_service_probe(self, port: int) -> Optional[bytes]:
        """Get appropriate probe to send to service"""
        probes = {
            80: b'HEAD / HTTP/1.0\r\n\r\n',
            443: b'HEAD / HTTP/1.0\r\n\r\n',
            8080: b'HEAD / HTTP/1.0\r\n\r\n',
            21: b'USER anonymous\r\n',
            25: b'EHLO scanner\r\n',
            110: b'USER test\r\n',
            143: b'a001 CAPABILITY\r\n',
            3306: b'\x00',  # MySQL ping
            1433: b'\x12\x01\x00\x34\x00\x00\x00\x00\x00\x00\x15\x00\x06\x01\x00\x1b\x00\x01\x02',  # TDS prelogin
        }
        return probes.get(port, b'')
    
    def _get_udp_probe(self, port: int) -> bytes:
        """Get UDP probe for specific services"""
        probes = {
            53: b'\x00\x00\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00',  # DNS status request
            123: b'\x1b' + b'\x00' * 47,  # NTP request
            161: b'\x30\x26\x02\x01\x00\x04\x06public\xa0\x19\x02\x04',  # SNMP get request
            500: b'\x00' * 8,  # IKE
        }
        return probes.get(port, b'\x00')
    
    def _safe_decode(self, data: bytes) -> str:
        """Safely decode banner data"""
        try:
            # Try UTF-8 first
            return data.decode('utf-8', errors='ignore').strip()[:100]  # Limit length
        except:
            # Fallback to latin-1
            try:
                return data.decode('latin-1', errors='ignore').strip()[:100]
            except:
                # Last resort - hex representation
                return data[:50].hex()
    
    def _identify_service(self, banner_data: bytes, port: int) -> str:
        """Identify service from banner"""
        # Check banner signatures
        for service, signatures in SERVICE_SIGNATURES.items():
            for sig in signatures:
                if sig in banner_data:
                    return service
        
        # Fall back to port-based identification
        return COMMON_SERVICES.get(port, 'Unknown')
    
    def _extract_version(self, banner_data: bytes) -> Optional[str]:
        """Extract version information from banner"""
        banner_str = self._safe_decode(banner_data)
        
        # Common version patterns
        import re
        patterns = [
            r'(\d+\.\d+\.\d+)',  # x.y.z
            r'v(\d+\.\d+)',      # vX.Y
            r'version (\S+)',    # version X
            r'Ver (\S+)',        # Ver X
        ]
        
        for pattern in patterns:
            match = re.search(pattern, banner_str, re.IGNORECASE)
            if match:
                return match.group(1)[:20]  # Limit version string length
        
        return None


class PingWorker(QThread):
    # Signals
    result_ready = pyqtSignal(str, bool, float, str)
    progress_update = pyqtSignal(str, int, int)  # status, current, total
    detailed_info = pyqtSignal(str, dict)  # ip, detailed_info
    port_scan_progress = pyqtSignal(int, int)  # scanned, total
    error_occurred = pyqtSignal(str, str)  # ip, error_message
    
    # Class-level thread pool for DNS resolution
    _dns_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    
    def __init__(self, ip: str, timeout_ms: int, profile: Dict[str, Any], 
                 port_range: Optional[Tuple[int, int]] = None):
        super().__init__()
        self.ip = ip
        self.timeout_ms = timeout_ms
        self.profile = profile.copy()  # Make a copy to avoid mutations
        self.port_range = port_range
        self.scanner = EnhancedPortScanner(ip, profile.get('port_timeout_ms', 300))
        self._stop_flag = threading.Event()
        self._progress_throttler = ProgressThrottler(min_interval=0.1)
        self._port_futures = []
        self._executor = None
        
    def run(self):
        """Main scanning thread with comprehensive error handling"""
        result = None
        try:
            # Initialize result dictionary
            result = {
                'ip': self.ip,
                'alive': False,
                'response_time': 0,
                'hostname': 'N/A',
                'detection_method': None,
                'open_ports': [],
                'port_details': {},
                'os_hint': 'Unknown',
                'mac_address': None,
                'scan_time': datetime.now().isoformat()
            }
            
            # Phase 1: Host detection
            if not self._stop_flag.is_set():
                self.progress_update.emit("Detecting host...", 1, 4)
                alive, response_time, method = self._detect_host()
                result['alive'] = alive
                result['response_time'] = response_time
                result['detection_method'] = method
            
            if not alive or self._stop_flag.is_set():
                # Emit detailed info first (even for down hosts)
                self.detailed_info.emit(self.ip, result)
                # Then emit result ready
                self.result_ready.emit(self.ip, False, response_time, "Host down")
                return
            
            # Phase 2: DNS resolution
            if not self._stop_flag.is_set():
                self.progress_update.emit("Resolving hostname...", 2, 4)
                result['hostname'] = self._resolve_hostname()
            
            # Phase 3: Port scanning
            if self.port_range and not self._stop_flag.is_set():
                self.progress_update.emit("Scanning ports...", 3, 4)
                result['open_ports'], result['port_details'] = self._scan_ports()
            
            # Phase 4: OS detection and final analysis
            if not self._stop_flag.is_set():
                self.progress_update.emit("Analyzing results...", 4, 4)
                result['os_hint'] = self._detect_os_hint(result)
                
                # Windows-specific: Try to get MAC address
                if self._is_local_network(self.ip):
                    result['mac_address'] = self._get_mac_address_windows()
            
            # Create summary
            summary = self._create_summary(result)
            
            # IMPORTANT: Emit detailed info FIRST
            self.detailed_info.emit(self.ip, result)
            
            # THEN emit result ready (this triggers table update)
            self.result_ready.emit(self.ip, True, response_time, summary)
            
        except Exception as e:
            # Comprehensive error handling
            error_msg = f"{type(e).__name__}: {str(e)}"
            self.error_occurred.emit(self.ip, error_msg)
            
            # Still emit a result even on error
            if result is None:
                result = {
                    'ip': self.ip,
                    'alive': False,
                    'response_time': 0,
                    'hostname': 'N/A',
                    'detection_method': 'Error',
                    'open_ports': [],
                    'port_details': {},
                    'os_hint': 'Unknown',
                    'mac_address': None,
                    'scan_time': datetime.now().isoformat(),
                    'error': error_msg
                }
            else:
                result['error'] = error_msg
                
            self.detailed_info.emit(self.ip, result)
            self.result_ready.emit(self.ip, False, 0, f"Error: {error_msg}")
        
        finally:
            # Cleanup
            self._cleanup()
    
    def stop(self):
        """Stop the scanning thread gracefully"""
        self._stop_flag.set()
        # Cancel port scan futures
        for future in self._port_futures:
            future.cancel()
    
    def _cleanup(self):
        """Clean up resources"""
        # Shutdown executor if created
        if self._executor:
            self._executor.shutdown(wait=False)
        self._port_futures.clear()
    
    def _detect_host(self) -> Tuple[bool, float, str]:
        """Multi-method host detection with early stop support"""
        start_time = time.time()
        
        # Method 1: ICMP ping (Windows-compatible)
        if not self._stop_flag.is_set() and self._icmp_ping_windows():
            response_time = (time.time() - start_time) * 1000
            return True, response_time, "ICMP"
        
        # Method 2: TCP connect to common ports
        if not self._stop_flag.is_set():
            tcp_result = self._tcp_ping()
            if tcp_result[0]:
                response_time = (time.time() - start_time) * 1000
                return True, response_time, f"TCP:{tcp_result[1]}"
        
        # Method 3: ARP check for local network (Windows)
        if not self._stop_flag.is_set() and self._is_local_network(self.ip):
            if self._arp_check_windows():
                response_time = (time.time() - start_time) * 1000
                return True, response_time, "ARP"
        
        # Host appears down
        return False, self.timeout_ms, "No response"
    
    def _icmp_ping_windows(self) -> bool:
        """Windows-specific ICMP ping implementation"""
        try:
            ping_cmd = [
                'ping', '-n', '2',  # 2 pings
                '-w', str(self.timeout_ms),  # timeout in ms
                '-4',  # Force IPv4
                self.ip
            ]
            
            # Properly hide console window
            startupinfo = None
            creationflags = 0
            
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = SW_HIDE
                creationflags = CREATE_NO_WINDOW
            
            result = subprocess.run(
                ping_cmd,
                capture_output=True,
                text=True,
                timeout=(self.timeout_ms / 1000) * 3,
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            # Check for success indicators in output
            output = result.stdout.lower()
            return 'ttl=' in output and 'unreachable' not in output
            
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
    
    def _tcp_ping(self) -> Tuple[bool, int]:
        """TCP connect scan to common ports"""
        # Try ports in order of likelihood
        quick_ports = [80, 443, 22, 3389, 445, 135, 8080, 21, 25, 110]
        
        for port in quick_ports:
            if self._stop_flag.is_set():
                break
                
            try:
                with SocketManager() as sock:
                    sock.settimeout(self.timeout_ms / 1000 / 2)
                    result = sock.connect_ex((self.ip, port))
                    
                    if result == 0:
                        return True, port
            except:
                continue
                
        return False, 0
    
    def _arp_check_windows(self) -> bool:
        """Windows ARP table check"""
        if sys.platform != 'win32':
            return False
            
        try:
            # First, try to connect to trigger ARP
            with SocketManager(type=socket.SOCK_DGRAM) as sock:
                sock.settimeout(0.1)
                sock.sendto(b'', (self.ip, 1))
            
            # Check ARP table
            result = subprocess.run(
                ['arp', '-a', self.ip],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            # Look for MAC address pattern
            import re
            mac_pattern = r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}'
            return bool(re.search(mac_pattern, result.stdout))
            
        except:
            return False
    
    def _resolve_hostname(self) -> str:
        """Resolve hostname with timeout using thread pool"""
        try:
            # Use thread pool for DNS resolution
            future = self._dns_executor.submit(socket.gethostbyaddr, self.ip)
            hostname, _, _ = future.result(timeout=2.0)
            return hostname
        except concurrent.futures.TimeoutError:
            return 'N/A'
        except Exception:
            return 'N/A'
    
    def _scan_ports(self) -> Tuple[List[int], Dict[int, Dict]]:
        """Enhanced parallel port scanning with proper cleanup"""
        if not self.port_range:
            return [], {}
            
        start_port, end_port = self.port_range
        
        # Determine ports to scan
        ports_to_scan = self._determine_ports_to_scan(start_port, end_port)
        
        if not ports_to_scan:
            return [], {}
        
        open_ports = []
        port_details = {}
        total_ports = len(ports_to_scan)
        scanned = 0
        
        # Use thread pool for parallel scanning
        max_workers = min(self.profile.get('parallel_workers', 30), len(ports_to_scan))
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
        try:
            # Submit all port scans
            future_to_port = {}
            for port in ports_to_scan:
                if self._stop_flag.is_set():
                    break
                    
                future = self._executor.submit(
                    self.scanner.scan_port_tcp, 
                    port, 
                    self.profile.get('banner_grab', False)
                )
                future_to_port[future] = port
                self._port_futures.append(future)
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_port, timeout=30):
                if self._stop_flag.is_set():
                    break
                    
                port = future_to_port[future]
                self._port_futures.remove(future)
                
                try:
                    result = future.result()
                    if result.is_open:
                        open_ports.append(port)
                        port_details[port] = result.to_dict()
                except Exception:
                    pass
                
                scanned += 1
                
                # Throttled progress updates
                if self._progress_throttler.should_update(scanned, total_ports):
                    self.port_scan_progress.emit(scanned, total_ports)
            
            # Emit final progress
            self.port_scan_progress.emit(total_ports, total_ports)
            
        except concurrent.futures.TimeoutError:
            # Scan timeout - return what we have
            pass
        finally:
            # Cancel remaining futures
            for future in self._port_futures:
                future.cancel()
            # Shutdown executor
            self._executor.shutdown(wait=False)
            self._executor = None
        
        open_ports.sort()
        return open_ports, port_details
    
    def _determine_ports_to_scan(self, start_port: int, end_port: int) -> List[int]:
        """Determine which ports to scan based on profile and range"""
        ports_to_scan = []
        
        if self.profile.get('ports') == 'common_1024':
            ports_to_scan = list(range(1, min(1025, end_port + 1)))
        elif isinstance(self.profile.get('ports'), list):
            # Use predefined port list, filtered by range
            ports_to_scan = [p for p in self.profile['ports'] 
                           if start_port <= p <= end_port]
        else:
            # Range-based scan
            total_range = end_port - start_port + 1
            
            if total_range > 1000:
                # Smart sampling for large ranges
                # Include priority ports in range
                priority_in_range = [p for p in PRIORITY_PORTS 
                                   if start_port <= p <= end_port]
                
                # Sample additional ports
                all_ports = set(range(start_port, end_port + 1))
                remaining_ports = list(all_ports - set(priority_in_range))
                
                if remaining_ports:
                    # Sample up to 200 additional ports
                    sample_size = min(200, len(remaining_ports))
                    sampled = random.sample(remaining_ports, sample_size)
                    ports_to_scan = priority_in_range + sampled
                else:
                    ports_to_scan = priority_in_range
            else:
                # Scan all ports in range
                ports_to_scan = list(range(start_port, end_port + 1))
        
        return ports_to_scan
    
    def _detect_os_hint(self, result: Dict) -> str:
        """Detect OS based on various indicators"""
        os_hints = []
        
        # TTL-based detection (from ping)
        ttl = self._get_ttl_from_ping()
        if ttl:
            if 60 <= ttl <= 64:
                os_hints.append("Linux/Unix")
            elif 120 <= ttl <= 128:
                os_hints.append("Windows")
            elif ttl == 255:
                os_hints.append("Network Device")
        
        # Port-based detection
        open_ports = set(result.get('open_ports', []))
        if open_ports:
            # Windows indicators
            if {135, 139, 445}.intersection(open_ports):
                os_hints.append("Windows")
            if 3389 in open_ports:
                os_hints.append("Windows (RDP)")
                
            # Linux/Unix indicators
            if 22 in open_ports and 3389 not in open_ports:
                os_hints.append("Linux/Unix")
                
            # Service-specific hints
            if {80, 443}.intersection(open_ports):
                os_hints.append("Web Server")
            if {3306, 5432}.intersection(open_ports):
                os_hints.append("Database Server")
        
        # Consolidate hints
        if not os_hints:
            return "Unknown"
        elif any("Windows" in hint for hint in os_hints):
            return "Windows"
        elif any("Linux" in hint or "Unix" in hint for hint in os_hints):
            return "Linux/Unix"
        elif "Network Device" in os_hints:
            return "Network Device"
        else:
            return os_hints[0]
    
    def _get_ttl_from_ping(self) -> Optional[int]:
        """Extract TTL from ping output"""
        if sys.platform != 'win32':
            return None
            
        try:
            result = subprocess.run(
                ['ping', '-n', '1', '-4', self.ip],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=CREATE_NO_WINDOW
            )
            
            import re
            ttl_match = re.search(r'TTL=(\d+)', result.stdout, re.IGNORECASE)
            if ttl_match:
                return int(ttl_match.group(1))
        except:
            pass
        return None
    
    def _get_mac_address_windows(self) -> Optional[str]:
        """Get MAC address on Windows"""
        if sys.platform != 'win32':
            return None
            
        try:
            result = subprocess.run(
                ['arp', '-a', self.ip],
                capture_output=True,
                text=True,
                timeout=2,
                creationflags=CREATE_NO_WINDOW
            )
            
            import re
            # Windows ARP output format
            lines = result.stdout.split('\n')
            for line in lines:
                if self.ip in line:
                    # Extract MAC address
                    mac_match = re.search(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', line)
                    if mac_match:
                        return mac_match.group(0).upper().replace('-', ':')
        except:
            pass
        return None
    
    def _is_local_network(self, ip: str) -> bool:
        """Check if IP is on local network"""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return ip_obj.is_private or ip_obj.is_loopback
        except:
            return False
    
    def _create_summary(self, result: Dict) -> str:
        """Create summary string for display"""
        parts = []
        
        # Hostname
        if result['hostname'] != 'N/A':
            parts.append(f"Host: {result['hostname']}")
        
        # OS hint
        if result['os_hint'] != 'Unknown':
            parts.append(f"OS: {result['os_hint']}")
        
        # Open ports summary
        if result['open_ports']:
            port_info = []
            for port in result['open_ports'][:5]:  # Show first 5
                details = result['port_details'].get(port, {})
                service = details.get('service', 'Unknown')
                port_info.append(f"{port}/{service}")
            
            ports_str = ', '.join(port_info)
            if len(result['open_ports']) > 5:
                ports_str += f" +{len(result['open_ports'])-5} more"
            parts.append(f"Ports: {ports_str}")
        
        # MAC address for local hosts
        if result['mac_address']:
            parts.append(f"MAC: {result['mac_address']}")
        
        return " | ".join(parts) if parts else "Host up"


# Export functions with validation
def export_scan_results(results: List[Dict], format: str = 'json') -> str:
    """Export scan results in various formats with validation"""
    if not results:
        return ""
        
    # Validate format
    valid_formats = ['json', 'csv', 'text']
    if format not in valid_formats:
        raise ValueError(f"Invalid format. Must be one of: {valid_formats}")
    
    if format == 'json':
        import json
        return json.dumps(results, indent=2, default=str)
    
    elif format == 'csv':
        import csv
        import io
        
        output = io.StringIO()
        
        # Flatten the results for CSV
        fieldnames = ['ip', 'alive', 'hostname', 'response_time', 
                     'detection_method', 'os_hint', 'mac_address', 
                     'open_ports_count', 'open_ports', 'scan_time']
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for result in results:
            flat_result = {
                'ip': result.get('ip', ''),
                'alive': result.get('alive', False),
                'hostname': result.get('hostname', 'N/A'),
                'response_time': f"{result.get('response_time', 0):.1f}",
                'detection_method': result.get('detection_method', ''),
                'os_hint': result.get('os_hint', 'Unknown'),
                'mac_address': result.get('mac_address', 'N/A'),
                'open_ports_count': len(result.get('open_ports', [])),
                'open_ports': ','.join(map(str, result.get('open_ports', []))),
                'scan_time': result.get('scan_time', '')
            }
            writer.writerow(flat_result)
        
        return output.getvalue()
    
    elif format == 'text':
        lines = ["Network Scan Results", "=" * 50, ""]
        
        # Summary
        total_hosts = len(results)
        active_hosts = sum(1 for r in results if r.get('alive'))
        lines.append(f"Total hosts scanned: {total_hosts}")
        lines.append(f"Active hosts found: {active_hosts}")
        lines.append("")
        
        # Active hosts details
        if active_hosts > 0:
            lines.append("Active Hosts:")
            lines.append("-" * 30)
            
            for result in results:
                if result.get('alive'):
                    line = f"{result['ip']:15} - {result.get('hostname', 'N/A'):30} - "
                    line += f"{result.get('os_hint', 'Unknown'):15} - "
                    
                    open_ports = result.get('open_ports', [])
                    if open_ports:
                        line += f"{len(open_ports)} ports open"
                        if len(open_ports) <= 5:
                            line += f" ({','.join(map(str, open_ports))})"
                    else:
                        line += "No open ports"
                    
                    if result.get('mac_address'):
                        line += f" - MAC: {result['mac_address']}"
                    
                    lines.append(line)
        
        return '\n'.join(lines)
    
    else:
        raise ValueError(f"Unsupported format: {format}")


def validate_ip_address(ip: str) -> bool:
    """Validate IP address or CIDR notation"""
    try:
        if '/' in ip:
            ipaddress.ip_network(ip, strict=False)
        else:
            ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def get_ip_range(start_ip: str, end_ip: str) -> List[str]:
    """Generate list of IPs between start and end IP with validation"""
    try:
        # Clean inputs
        start_ip = start_ip.strip()
        end_ip = end_ip.strip() if end_ip else ""
        
        # Single IP
        if not end_ip:
            if '/' in start_ip:
                # CIDR notation
                network = ipaddress.ip_network(start_ip, strict=False)
                if network.num_addresses > 1024:
                    raise ValueError(f"Network too large: {network.num_addresses} addresses (max 1024)")
                return [str(ip) for ip in network.hosts()]
            else:
                # Single IP
                if not validate_ip_address(start_ip):
                    raise ValueError(f"Invalid IP address: {start_ip}")
                return [start_ip]
        
        # IP range
        start = ipaddress.ip_address(start_ip)
        end = ipaddress.ip_address(end_ip)
        
        if start.version != end.version:
            raise ValueError("IP versions don't match")
        if start > end:
            raise ValueError("Start IP must be less than or equal to End IP")
        
        if start == end:
            return [str(start)]
            
        # Calculate range size
        range_size = int(end) - int(start) + 1
        if range_size > 1024:
            raise ValueError(f"IP range too large: {range_size} addresses (max 1024)")
        
        return [str(ipaddress.ip_address(i)) 
               for i in range(int(start), int(end) + 1)]
        
    except Exception as e:
        raise ValueError(f"Invalid IP range: {str(e)}")


# Constants (updated)
DEFAULT_TIMEOUT_MS = 1000
MAX_CONCURRENT_THREADS = 100
BATCH_UPDATE_SIZE = 10
MAX_IP_RANGE = 1024

# Common port ranges with descriptions
COMMON_PORTS = {
    "Web Services (80, 443, 8080, 8443)": (80, 8443),
    "Mail Services (25, 110, 143, 587, 993, 995)": (25, 995),
    "File Services (20-22, 445, 3389)": (20, 3389),
    "Database Services (1433, 3306, 5432)": (1433, 5432),
    "Quick Scan (Common Ports Only)": "priority",
    "Standard Scan (1-1024)": (1, 1024),
    "Extended Scan (1-10000)": (1, 10000),
    "Full Scan (1-65535)": (1, 65535)
}