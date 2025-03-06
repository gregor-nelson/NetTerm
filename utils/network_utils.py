"""
Network utility functions for the ping scanner module.
"""
import subprocess
import socket
import ipaddress
import sys


def get_network_adapters():
    """
    Get network adapter information by calling ipconfig command.
    
    Returns:
        list: List of dicts with adapter information
    """
    try:
        # Run ipconfig command with hidden window
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        
        # Run ipconfig with all details
        result = subprocess.run(['ipconfig', '/all'], 
                              capture_output=True, 
                              text=True, 
                              startupinfo=startupinfo)
        
        if result.returncode != 0:
            # Command failed
            return []
            
        output = result.stdout
        
        # Parse the ipconfig output
        adapters_info = []
        current_adapter = None
        adapter_section = False
        
        for line in output.splitlines():
            line = line.rstrip()
            
            # Empty line - reset the state
            if not line.strip():
                continue
                
            # Check for adapter headers (not indented)
            if not line.startswith(" ") and "adapter" in line.lower() and ":" in line:
                # New adapter section
                adapter_name = line.split(":", 1)[0].strip()
                
                # Start a new adapter
                current_adapter = {
                    "adapter_name": adapter_name,
                    "ip_addresses": [],
                    "subnet_masks": [],
                    "mac_address": "N/A",
                    "default_gateway": "N/A"
                }
                adapters_info.append(current_adapter)
                adapter_section = True
                continue
            
            # Only process indented lines (adapter properties) if we're in an adapter section
            if adapter_section and line.startswith(" ") and current_adapter is not None:
                # Try to extract property: value pairs
                parts = line.strip().split(":", 1)
                if len(parts) == 2:
                    key, value = parts[0].strip(), parts[1].strip()
                    
                    # Process different properties
                    if "IPv4 Address" in key and value:
                        # Remove (Preferred) suffix if present
                        ip = value.split('(')[0].strip()
                        current_adapter["ip_addresses"].append(ip)
                    elif "Subnet Mask" in key and value:
                        current_adapter["subnet_masks"].append(value)
                    elif "Physical Address" in key and value and value != "":
                        current_adapter["mac_address"] = value
                    elif "Default Gateway" in key and value and value != "":
                        current_adapter["default_gateway"] = value
        
        # Filter adapters that have IP addresses
        filtered_adapters = [adapter for adapter in adapters_info if adapter.get("ip_addresses")]
        
        return filtered_adapters
    except Exception as e:
        print(f"Error getting network adapters: {str(e)}")
        return []


def parse_ip_range(start_ip, end_ip=None):
    """
    Parse IP range from start and end IPs or CIDR notation.
    
    Args:
        start_ip: Starting IP address or CIDR notation (e.g., 192.168.1.0/24)
        end_ip: Ending IP address (optional)
        
    Returns:
        list: List of IP addresses in the range
    """
    # Check if start_ip contains CIDR notation
    if '/' in start_ip:
        try:
            network = ipaddress.ip_network(start_ip, strict=False)
            return [str(ip) for ip in network.hosts()]
        except ValueError:
            raise ValueError(f"Invalid CIDR notation: {start_ip}")
    
    # Check if end_ip is provided
    if end_ip:
        try:
            start = ipaddress.ip_address(start_ip)
            end = ipaddress.ip_address(end_ip)
            
            # Ensure start <= end
            if start > end:
                start, end = end, start
                
            # Generate IP range
            return [str(ipaddress.ip_address(ip)) for ip in range(int(start), int(end) + 1)]
        except ValueError:
            raise ValueError("Invalid IP addresses provided")
    
    # Single IP address
    try:
        ipaddress.ip_address(start_ip)  # Validate IP
        return [start_ip]
    except ValueError:
        raise ValueError(f"Invalid IP address: {start_ip}")


def ping_host(ip_address, timeout_ms=1000):
    """
    Ping a host to check if it's reachable.
    
    Args:
        ip_address: IP address to ping
        timeout_ms: Timeout in milliseconds
        
    Returns:
        tuple: (success, response_time_ms)
    """
    try:
        # Configure ping command based on platform
        platform = get_platform()
        if platform == "windows":
            cmd = ['ping', '-n', '1', '-w', str(timeout_ms), ip_address]
        else:  # Linux/Unix
            cmd = ['ping', '-c', '1', '-W', str(timeout_ms / 1000), ip_address]
        
        # Hide console window on Windows
        startupinfo = None
        if platform == "windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        # Execute ping command
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            startupinfo=startupinfo,
            timeout=timeout_ms / 1000 + 1  # Add 1 second to timeout
        )
        
        # Parse output to determine success and response time
        output = result.stdout.lower()
        
        if platform == "windows":
            success = "reply from" in output and "destination host unreachable" not in output
        else:
            success = " 0% packet loss" in output
            
        # Extract response time
        response_time = 0
        if success:
            if platform == "windows":
                time_parts = output.split("time=")
                if len(time_parts) > 1:
                    time_str = time_parts[1].split("ms")[0].strip()
                    response_time = float(time_str)
            else:
                time_parts = output.split("time=")
                if len(time_parts) > 1:
                    time_str = time_parts[1].split(" ")[0].strip()
                    response_time = float(time_str)
        
        return success, response_time
            
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False, 0
    except Exception as e:
        print(f"Error pinging {ip_address}: {str(e)}")
        return False, 0


def get_hostname(ip_address):
    """
    Resolve hostname from IP address.
    
    Args:
        ip_address: IP address to resolve
        
    Returns:
        str: Hostname or empty string if not resolved
    """
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname
    except (socket.herror, socket.gaierror):
        return ""


def scan_ports(ip_address, port_range=(1, 1024), timeout=0.5):
    """
    Scan for open ports on a given IP address.
    
    Args:
        ip_address: IP address to scan
        port_range: Tuple of (start_port, end_port)
        timeout: Connection timeout in seconds
        
    Returns:
        list: List of open ports
    """
    open_ports = []
    start_port, end_port = port_range
    
    for port in range(start_port, end_port + 1):
        try:
            # Create socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            
            # Try to connect
            result = s.connect_ex((ip_address, port))
            if result == 0:
                # Port is open
                service = get_service_name(port)
                open_ports.append((port, service))
            
            # Close socket
            s.close()
            
        except (socket.timeout, socket.error):
            pass
        
    return open_ports


def get_service_name(port):
    """
    Get service name for a port number.
    
    Args:
        port: Port number
        
    Returns:
        str: Service name or empty string if not known
    """
    try:
        return socket.getservbyport(port)
    except (socket.error, OSError):
        # Common services that might not be in the system database
        common_services = {
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            443: "HTTPS",
            3389: "RDP",
            8080: "HTTP-Alt"
        }
        return common_services.get(port, "")


def get_platform():
    """
    Determine the platform (operating system).
    
    Returns:
        str: "windows", "linux", or "mac"
    """
    import platform
    system = platform.system().lower()
    
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "mac"
    else:
        return "unknown"