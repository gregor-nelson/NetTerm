"""
Device identification utilities for serial ports.
"""
import re
import platform
import subprocess
import json
import os
from typing import Dict, List, Optional, Tuple

try:
    import winreg
except ImportError:
    winreg = None


# Enhanced chipset information with capabilities and detailed specs
CHIPSET_DATABASE = {
    # FTDI Family
    "0403:6001": {
        "chipset_family": "FTDI",
        "chipset_variant": "FT232R",
        "uart_channels": 1,
        "max_baudrate": 3000000,
        "gpio_pins": 4,
        "features": ["USB 2.0", "3.3V/5V I/O", "Bit-bang mode", "EEPROM"],
        "driver_type": "VCP/D2XX",
        "known_issues": ["Some clones may have stability issues"]
    },
    "0403:6010": {
        "chipset_family": "FTDI",
        "chipset_variant": "FT2232C/D/H",
        "uart_channels": 2,
        "max_baudrate": 12000000,
        "gpio_pins": 8,
        "features": ["USB 2.0", "Dual channel", "MPSSE", "JTAG/SPI/I2C"],
        "driver_type": "VCP/D2XX",
        "known_issues": []
    },
    "0403:6014": {
        "chipset_family": "FTDI",
        "chipset_variant": "FT232H",
        "uart_channels": 1,
        "max_baudrate": 12000000,
        "gpio_pins": 16,
        "features": ["USB 2.0 Hi-Speed", "MPSSE", "FIFO mode", "JTAG/SPI/I2C"],
        "driver_type": "VCP/D2XX",
        "known_issues": []
    },
    
    # Silicon Labs CP210x Family
    "10C4:EA60": {
        "chipset_family": "Silicon Labs",
        "chipset_variant": "CP2102/CP2109",
        "uart_channels": 1,
        "max_baudrate": 2000000,
        "gpio_pins": 4,
        "features": ["USB 2.0", "3.3V I/O", "Hardware flow control"],
        "driver_type": "VCP",
        "known_issues": []
    },
    "10C4:EA70": {
        "chipset_family": "Silicon Labs",
        "chipset_variant": "CP2105",
        "uart_channels": 2,
        "max_baudrate": 2000000,
        "gpio_pins": 8,
        "features": ["USB 2.0", "Dual UART", "GPIO"],
        "driver_type": "VCP",
        "known_issues": []
    },
    
    # WCH CH340 Family
    "1A86:7523": {
        "chipset_family": "WCH",
        "chipset_variant": "CH340G",
        "uart_channels": 1,
        "max_baudrate": 2000000,
        "gpio_pins": 0,
        "features": ["USB 2.0", "Low cost", "Basic UART"],
        "driver_type": "VCP",
        "known_issues": ["Driver quality varies on different OS versions"]
    },
    
    # Prolific Family
    "067B:2303": {
        "chipset_family": "Prolific",
        "chipset_variant": "PL2303",
        "uart_channels": 1,
        "max_baudrate": 12000000,
        "gpio_pins": 0,
        "features": ["USB 1.1/2.0", "Hardware flow control"],
        "driver_type": "VCP",
        "known_issues": ["Many counterfeit chips exist", "Driver compatibility issues"]
    },
    
    # Intel AMT SOL (Serial-over-LAN) Family
    "8086:9D3D": {
        "chipset_family": "Intel AMT",
        "chipset_variant": "SOL (Serial-over-LAN)",
        "uart_channels": 1,
        "max_baudrate": 115200,
        "gpio_pins": 0,
        "features": ["Remote Management", "Network-based Serial", "BIOS/UEFI Access", "Out-of-band Management"],
        "driver_type": "Intel AMT SOL",
        "known_issues": ["Requires AMT to be enabled and configured", "Network connectivity dependent"]
    },
    "8086:9DE3": {
        "chipset_family": "Intel AMT",
        "chipset_variant": "SOL (Serial-over-LAN) - Coffee Lake",
        "uart_channels": 1,
        "max_baudrate": 115200,
        "gpio_pins": 0,
        "features": ["Remote Management", "Network-based Serial", "BIOS/UEFI Access", "Out-of-band Management"],
        "driver_type": "Intel AMT SOL",
        "known_issues": ["Requires AMT to be enabled and configured", "Network connectivity dependent"]
    },
    "8086:A363": {
        "chipset_family": "Intel AMT",
        "chipset_variant": "SOL (Serial-over-LAN) - Cannon Lake",
        "uart_channels": 1,
        "max_baudrate": 115200,
        "gpio_pins": 0,
        "features": ["Remote Management", "Network-based Serial", "BIOS/UEFI Access", "Out-of-band Management"],
        "driver_type": "Intel AMT SOL",
        "known_issues": ["Requires AMT to be enabled and configured", "Network connectivity dependent"]
    }
}

# Dictionary of VID:PID to device information (enhanced)
KNOWN_DEVICES = {
    # FTDI Devices
    "0403:6001": {
        "name": "FTDI FT232R USB-Serial Adapter",
        "description": "Single-channel USB to UART converter with GPIO and bit-bang capabilities",
        "manufacturer": "FTDI",
        "device_class": "Communication Device",
        "confidence": 0.95
    },
    "0403:6010": {
        "name": "FTDI FT2232C/D/H Dual USB-Serial Adapter", 
        "description": "Dual-channel USB to UART/FIFO converter with MPSSE support",
        "manufacturer": "FTDI",
        "device_class": "Communication Device",
        "confidence": 0.95
    },
    "0403:6014": {
        "name": "FTDI FT232H Hi-Speed USB-Serial Adapter",
        "description": "Single-channel Hi-Speed USB to UART/FIFO/SPI/I2C/JTAG converter",
        "manufacturer": "FTDI",
        "device_class": "Communication Device",
        "confidence": 0.95
    },
    
    # Prolific Devices
    "067B:2303": {
        "name": "Prolific PL2303 USB-Serial Adapter",
        "description": "Common USB to Serial adapter chip",
        "manufacturer": "Prolific"
    },
    
    # Silicon Labs Devices
    "10C4:EA60": {
        "name": "Silicon Labs CP210x USB-Serial Adapter",
        "description": "USB to Serial bridge chip used in many IoT devices",
        "manufacturer": "Silicon Labs"
    },
    
    # Arduino Devices
    "2341:0043": {
        "name": "Arduino Uno",
        "description": "Arduino Uno development board",
        "manufacturer": "Arduino"
    },
    "2341:0042": {
        "name": "Arduino Mega 2560",
        "description": "Arduino Mega 2560 development board",
        "manufacturer": "Arduino"
    },
    "2341:0036": {
        "name": "Arduino Leonardo",
        "description": "Arduino Leonardo development board",
        "manufacturer": "Arduino"
    },
    "2341:0037": {
        "name": "Arduino Micro",
        "description": "Arduino Micro development board",
        "manufacturer": "Arduino"
    },
    "2341:0041": {
        "name": "Arduino Yun",
        "description": "Arduino Yun development board",
        "manufacturer": "Arduino"
    },
    "2341:8036": {
        "name": "Arduino Leonardo (bootloader mode)",
        "description": "Arduino Leonardo in bootloader mode",
        "manufacturer": "Arduino"
    },
    "2341:0052": {
        "name": "Arduino Due",
        "description": "Arduino Due development board (Programming Port)",
        "manufacturer": "Arduino"
    },
    "2341:0053": {
        "name": "Arduino Due",
        "description": "Arduino Due development board (Native USB Port)",
        "manufacturer": "Arduino"
    },
    "2341:0054": {
        "name": "Arduino Zero/M0 Pro",
        "description": "Arduino Zero or M0 Pro development board",
        "manufacturer": "Arduino"
    },
    "2341:8036": {
        "name": "Arduino Leonardo (bootloader mode)",
        "description": "Arduino Leonardo in bootloader mode",
        "manufacturer": "Arduino"
    },
    "2341:8041": {
        "name": "Arduino Yun (bootloader mode)",
        "description": "Arduino Yun in bootloader mode", 
        "manufacturer": "Arduino"
    },
    
    # ESP Devices
    "10C4:EA60": {
        "name": "ESP32/ESP8266 Development Board",
        "description": "Espressif ESP32 or ESP8266 based development board",
        "manufacturer": "Espressif"
    },
    
    # Raspberry Pi Devices
    "2E8A:0005": {
        "name": "Raspberry Pi Pico",
        "description": "Raspberry Pi Pico microcontroller board",
        "manufacturer": "Raspberry Pi Foundation"
    },
    
    # Teensy Devices
    "16C0:0483": {
        "name": "Teensy USB Development Board",
        "description": "PJRC Teensy development board",
        "manufacturer": "PJRC"
    },
    
    # Microchip/Atmel
    "03EB:2404": {
        "name": "Microchip/Atmel AVR Programmer",
        "description": "USB AVR programmer for Atmel microcontrollers",
        "manufacturer": "Microchip/Atmel"
    },
    
    # Texas Instruments
    "0451:F432": {
        "name": "Texas Instruments Launchpad",
        "description": "TI MSP430 or other Launchpad development board",
        "manufacturer": "Texas Instruments"
    },
    
    # STMicroelectronics
    "0483:374B": {
        "name": "STM32 USB CDC Device",
        "description": "STM32 development board",
        "manufacturer": "STMicroelectronics",
        "device_class": "Communication Device",
        "confidence": 0.90
    },
    "0483:5740": {
        "name": "STM32 Virtual COM Port",
        "description": "STM32 microcontroller with USB",
        "manufacturer": "STMicroelectronics",
        "device_class": "Communication Device",
        "confidence": 0.90
    },
    
    # Intel Active Management Technology (AMT) SOL
    "8086:9D3D": {
        "name": "Intel AMT Serial-over-LAN (SOL)",
        "description": "Intel Active Management Technology Serial-over-LAN interface for remote management",
        "manufacturer": "Intel Corporation",
        "device_class": "Management Interface",
        "confidence": 0.98
    },
    "8086:9DE3": {
        "name": "Intel AMT SOL - Coffee Lake Platform",
        "description": "Intel Active Management Technology Serial-over-LAN for Coffee Lake chipset",
        "manufacturer": "Intel Corporation",
        "device_class": "Management Interface",
        "confidence": 0.98
    },
    "8086:A363": {
        "name": "Intel AMT SOL - Cannon Lake Platform",
        "description": "Intel Active Management Technology Serial-over-LAN for Cannon Lake chipset",
        "manufacturer": "Intel Corporation",
        "device_class": "Management Interface",
        "confidence": 0.98
    }
}


def identify_device_by_vid_pid(vid, pid):
    """
    Identify a device based on its Vendor ID and Product ID.
    
    Args:
        vid: Vendor ID (integer)
        pid: Product ID (integer)
        
    Returns:
        dict: Device information or None if not identified
    """
    if vid is None or pid is None:
        return None
        
    vid_pid = f"{vid:04X}:{pid:04X}"
    return KNOWN_DEVICES.get(vid_pid)


def identify_device_by_description(description):
    """
    Try to identify a device based on its description string.
    
    Args:
        description: Device description string
        
    Returns:
        dict: Device information or None if not identified
    """
    if not description:
        return None
        
    description = description.lower()
    
    # Check for FTDI devices
    if "ftdi" in description or "ft232" in description:
        return {
            "name": "FTDI USB-Serial Adapter",
            "description": "USB to Serial adapter based on FTDI chipset",
            "manufacturer": "FTDI"
        }
    
    # Check for Prolific devices
    if "prolific" in description or "pl2303" in description:
        return {
            "name": "Prolific USB-Serial Adapter",
            "description": "USB to Serial adapter based on Prolific chipset",
            "manufacturer": "Prolific"
        }
    
    # Check for Silicon Labs devices
    if "silicon labs" in description or "cp210" in description:
        return {
            "name": "Silicon Labs USB-Serial Adapter",
            "description": "USB to Serial adapter based on Silicon Labs chipset",
            "manufacturer": "Silicon Labs"
        }
    
    # Check for Arduino devices
    if "arduino" in description:
        return {
            "name": "Arduino Device",
            "description": "Arduino development board",
            "manufacturer": "Arduino"
        }
    
    # Check for ESP devices
    if "esp32" in description or "esp8266" in description:
        return {
            "name": "Espressif Device",
            "description": "ESP32 or ESP8266 development board",
            "manufacturer": "Espressif"
        }
    
    # Check for Raspberry Pi devices
    if "raspberry" in description or "rpi" in description or "pico" in description:
        return {
            "name": "Raspberry Pi Device",
            "description": "Raspberry Pi or Pico board",
            "manufacturer": "Raspberry Pi Foundation",
            "device_class": "Development Board",
            "confidence": 0.85
        }
    
    # Check for Intel AMT SOL devices
    if any(term in description for term in ["intel", "amt", "active management", "serial over lan", "sol"]):
        if "active management" in description or "amt" in description:
            return {
                "name": "Intel AMT Serial-over-LAN",
                "description": "Intel Active Management Technology Serial-over-LAN interface",
                "manufacturer": "Intel Corporation",
                "device_class": "Management Interface",
                "confidence": 0.92
            }
        elif "intel" in description and "sol" in description:
            return {
                "name": "Intel SOL Device",
                "description": "Intel Serial-over-LAN capable device",
                "manufacturer": "Intel Corporation",
                "device_class": "Management Interface",
                "confidence": 0.80
            }
    
    return None


def get_device_driver_recommendations(device_info):
    """
    Get driver recommendations for a specific device.
    
    Args:
        device_info: Device information dict or manufacturer string
        
    Returns:
        str: Driver recommendations
    """
    manufacturer = device_info
    if isinstance(device_info, dict):
        manufacturer = device_info.get("manufacturer", "")
    
    manufacturer = manufacturer.lower()
    
    if "ftdi" in manufacturer:
        return (
            "FTDI Driver Recommendations:\n"
            "- Windows: Download drivers from https://ftdichip.com/drivers/\n"
            "- macOS: FTDI drivers are built into macOS, but updated drivers are available\n"
            "- Linux: FTDI drivers are included in most Linux distributions\n"
            "- For virtual COM port, use the VCP driver\n"
            "- For direct API access, use D2XX driver"
        )
    
    if "prolific" in manufacturer:
        return (
            "Prolific Driver Recommendations:\n"
            "- Windows: Download drivers from Prolific website\n"
            "- macOS: Download drivers from Prolific website\n"
            "- Linux: Drivers are included in most Linux distributions\n"
            "- Warning: Many counterfeit PL2303 chips exist with compatibility issues"
        )
    
    if "silicon labs" in manufacturer:
        return (
            "Silicon Labs Driver Recommendations:\n"
            "- Windows: Download CP210x drivers from Silicon Labs website\n"
            "- macOS: Download CP210x drivers from Silicon Labs website\n"
            "- Linux: CP210x drivers are included in most Linux distributions"
        )
    
    if "arduino" in manufacturer:
        return (
            "Arduino Driver Recommendations:\n"
            "- Windows: Install Arduino IDE which includes necessary drivers\n"
            "- macOS: Install Arduino IDE which includes necessary drivers\n"
            "- Linux: Install Arduino IDE and ensure user is in 'dialout' group\n"
            "- For older Arduino models, FTDI drivers may be needed\n"
            "- For Arduino Uno and newer, built-in drivers are usually sufficient"
        )
    
    if "espressif" in manufacturer:
        return (
            "Espressif Driver Recommendations:\n"
            "- Windows: Install CP210x or CH340 drivers depending on board\n"
            "- macOS: Install CP210x or CH340 drivers depending on board\n"
            "- Linux: CP210x and CH340 drivers are usually included\n"
            "- Install ESP-IDF or Arduino ESP32 framework for development"
        )
    
    if "intel" in manufacturer and ("amt" in manufacturer.lower() or "sol" in manufacturer.lower()):
        return (
            "Intel AMT SOL Driver Recommendations:\n"
            "- Windows: Install Intel Active Management Technology drivers from Intel website\n"            
            "- Ensure Intel AMT is enabled in BIOS/UEFI settings\n"
            "- Configure AMT through Intel Setup and Configuration Service (SCS)\n"
            "- Verify network connectivity for SOL functionality\n"
            "- Use Intel AMT SDK or third-party AMT management tools\n"
            "- Default SOL settings: 115200 baud, 8N1, no flow control\n"
            "- Troubleshooting: Check AMT firmware version and MEBx settings"
        )
    
    # Default recommendations
    return (
        "General USB-Serial Driver Recommendations:\n"
        "- Ensure you have the latest drivers for your device\n"
        "- Windows: Check Device Manager for driver status\n"
        "- macOS: Check System Information > USB for device status\n"
        "- Linux: Run 'lsusb' and 'dmesg' to check device status"
    )


def detect_port_speed(port_name, test_speeds=None):
    """
    Attempt to detect the operational speed of a serial port.
    
    Args:
        port_name: Serial port to test
        test_speeds: List of baudrates to test (default: common rates)
        
    Returns:
        int: Most likely baudrate or None if detection failed
    """
    import serial
    import time
    
    if test_speeds is None:
        test_speeds = [115200, 57600, 38400, 19200, 9600, 4800, 2400, 1200]
    
    for baudrate in test_speeds:
        try:
            # Open port at current test speed
            ser = serial.Serial(port_name, baudrate=baudrate, timeout=0.5)
            
            # Send a basic query and see if we get valid response
            ser.write(b"\r\n")
            time.sleep(0.1)
            
            # Read any response
            response = ser.read(100)
            
            # If we got reasonable-looking data, this might be the right speed
            if response and len(response) > 2 and (
                any(b for b in response if b >= 32 and b <= 126)  # Printable ASCII
            ):
                ser.close()
                return baudrate
                
            # Try sending common commands for various devices
            test_commands = [
                b"AT\r\n",          # AT modems, ESP8266, Bluetooth modules
                b"??\r\n",          # Some serial devices
                b"help\r\n",        # Common command-line interfaces
                b"version\r\n",     # Common version command
            ]
            
            for cmd in test_commands:
                ser.write(cmd)
                time.sleep(0.2)
                response = ser.read(100)
                
                # Check for reasonable response
                if response and len(response) > 2 and (
                    any(b for b in response if b >= 32 and b <= 126)  # Printable ASCII
                ):
                    ser.close()
                    return baudrate
            
            ser.close()
            
        except serial.SerialException:
            # Skip any errors and continue with next baudrate
            pass
    
    return None  # Could not detect baudrate


def get_usb_descriptor_info(vid: int, pid: int) -> Optional[Dict]:
    """
    Get detailed USB descriptor information for a device.
    
    Args:
        vid: Vendor ID (integer)
        pid: Product ID (integer)
        
    Returns:
        dict: USB descriptor information or None if not available
    """
    system = platform.system()
    vid_pid_str = f"{vid:04X}:{pid:04X}"
    
    try:
        if system == "Windows":
            return _get_windows_usb_info(vid, pid)
        elif system == "Linux":
            return _get_linux_usb_info(vid, pid)
        elif system == "Darwin":  # macOS
            return _get_macos_usb_info(vid, pid)
    except Exception:
        pass
    
    return None


def _get_windows_usb_info(vid: int, pid: int) -> Optional[Dict]:
    """Get USB descriptor info on Windows using registry and WMI."""
    if not winreg:
        return None
        
    try:
        # Try to get device info from Windows registry
        import wmi
        c = wmi.WMI()
        
        for device in c.Win32_PnPEntity():
            if device.DeviceID and f"VID_{vid:04X}&PID_{pid:04X}" in device.DeviceID:
                return {
                    "manufacturer": device.Manufacturer or "Unknown",
                    "product": device.Name or "Unknown", 
                    "serial_number": _extract_serial_from_device_id(device.DeviceID),
                    "device_class": device.PNPClass or "Unknown",
                    "driver_version": device.DriverVersion or "Unknown",
                    "driver_date": device.DriverDate or "Unknown"
                }
    except ImportError:
        pass
    
    return None


def _get_linux_usb_info(vid: int, pid: int) -> Optional[Dict]:
    """Get USB descriptor info on Linux using lsusb and sysfs."""
    try:
        # Try lsusb first for detailed info
        result = subprocess.run(['lsusb', '-d', f'{vid:04x}:{pid:04x}', '-v'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            output = result.stdout
            info = {}
            
            # Parse lsusb verbose output
            for line in output.split('\n'):
                line = line.strip()
                if 'iManufacturer' in line and 'idManufacturer' not in line:
                    info['manufacturer'] = line.split(None, 2)[-1] if len(line.split(None, 2)) > 2 else "Unknown"
                elif 'iProduct' in line and 'idProduct' not in line:
                    info['product'] = line.split(None, 2)[-1] if len(line.split(None, 2)) > 2 else "Unknown"
                elif 'iSerial' in line:
                    info['serial_number'] = line.split(None, 2)[-1] if len(line.split(None, 2)) > 2 else "Unknown"
                elif 'bDeviceClass' in line:
                    info['device_class'] = line.split(None, 2)[-1] if len(line.split(None, 2)) > 2 else "Unknown"
            
            return info
            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return None


def _get_macos_usb_info(vid: int, pid: int) -> Optional[Dict]:
    """Get USB descriptor info on macOS using system_profiler."""
    try:
        result = subprocess.run(['system_profiler', 'SPUSBDataType', '-json'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return _parse_macos_usb_data(data, vid, pid)
            
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    
    return None


def _parse_macos_usb_data(data: Dict, vid: int, pid: int) -> Optional[Dict]:
    """Parse macOS system_profiler USB data recursively."""
    def search_usb_tree(items):
        for item in items:
            if item.get('vendor_id') == f'0x{vid:04x}' and item.get('product_id') == f'0x{pid:04x}':
                return {
                    'manufacturer': item.get('manufacturer', 'Unknown'),
                    'product': item.get('_name', 'Unknown'),
                    'serial_number': item.get('serial_num', 'Unknown'),
                    'device_class': 'Communication Device',  # Simplified for serial devices
                }
            
            # Recursively search in nested items
            if '_items' in item:
                result = search_usb_tree(item['_items']) 
                if result:
                    return result
        return None
    
    return search_usb_tree(data.get('SPUSBDataType', []))


def _extract_serial_from_device_id(device_id: str) -> str:
    """Extract serial number from Windows device ID."""
    parts = device_id.split('\\')
    for part in parts:
        if len(part) > 8 and not any(x in part.upper() for x in ['VID_', 'PID_', 'REV_']):
            return part
    return "Unknown"


def get_enhanced_device_info(vid: int, pid: int, description: str = None) -> Dict:
    """
    Get comprehensive device information including chipset details and Intel AMT detection.
    
    Args:
        vid: Vendor ID (integer)
        pid: Product ID (integer)  
        description: Device description string (optional)
        
    Returns:
        dict: Comprehensive device information with confidence scoring
    """
    vid_pid_str = f"{vid:04X}:{pid:04X}"
    
    # Check for Intel AMT SOL devices first (special case)
    is_intel_amt = False
    if vid == 0x8086:  # Intel Corporation
        is_intel_amt = True
    elif description:
        intel_amt_patterns = ['intel', 'amt', 'active management', 'serial over lan', 'sol']
        is_intel_amt = any(pattern in description.lower() for pattern in intel_amt_patterns)
    
    # Start with basic device info
    device_info = identify_device_by_vid_pid(vid, pid)
    if not device_info and description:
        device_info = identify_device_by_description(description)
    
    # Get chipset information
    chipset_info = CHIPSET_DATABASE.get(vid_pid_str, {})
    
    # Get USB descriptor information (may not apply to Intel AMT SOL)
    usb_info = {}
    if not is_intel_amt:
        usb_info = get_usb_descriptor_info(vid, pid) or {}
    
    # For Intel AMT devices, get specialized AMT information
    amt_info = {}
    if is_intel_amt:
        amt_ports = detect_intel_amt_sol_ports()
        for amt_port in amt_ports:
            if f"{vid:04X}:{pid:04X}" in str(amt_port.get('device_id', '')).upper():
                amt_info = amt_port
                break
    
    # Combine all information
    enhanced_info = {
        'basic_info': device_info or {
            'name': 'Unknown Device',
            'description': 'Could not identify device type specifically',
            'manufacturer': 'Unknown',
            'confidence': 0.1
        },
        'chipset_info': chipset_info,
        'usb_descriptor': usb_info,
        'amt_info': amt_info,
        'is_intel_amt': is_intel_amt,
        'identification_method': []
    }
    
    # Track how device was identified
    if device_info:
        if vid_pid_str in KNOWN_DEVICES:
            enhanced_info['identification_method'].append('VID:PID Database Match')
        else:
            enhanced_info['identification_method'].append('Description Pattern Match')
    
    if chipset_info:
        enhanced_info['identification_method'].append('Chipset Database Match')
        
    if usb_info:
        enhanced_info['identification_method'].append('USB Descriptor Analysis')
        
    if amt_info:
        enhanced_info['identification_method'].append('Intel AMT SOL Detection')
    
    return enhanced_info


def get_chipset_capabilities(vid: int, pid: int) -> Dict:
    """
    Get detailed chipset capabilities and specifications.
    
    Args:
        vid: Vendor ID (integer)
        pid: Product ID (integer)
        
    Returns:
        dict: Chipset capabilities and specifications
    """
    vid_pid_str = f"{vid:04X}:{pid:04X}"
    chipset_info = CHIPSET_DATABASE.get(vid_pid_str, {})
    
    if not chipset_info:
        return {
            'family': 'Unknown',
            'capabilities': 'No specific chipset information available',
            'recommendations': 'Use generic USB-serial drivers'
        }
    
    capabilities = []
    
    # Build capability description
    if chipset_info.get('uart_channels', 0) > 1:
        capabilities.append(f"{chipset_info['uart_channels']} UART channels")
    
    if chipset_info.get('max_baudrate'):
        capabilities.append(f"Max baudrate: {chipset_info['max_baudrate']:,} bps")
        
    if chipset_info.get('gpio_pins', 0) > 0:
        capabilities.append(f"{chipset_info['gpio_pins']} GPIO pins")
    
    if chipset_info.get('features'):
        capabilities.extend(chipset_info['features'])
    
    result = {
        'family': chipset_info.get('chipset_family', 'Unknown'),
        'variant': chipset_info.get('chipset_variant', 'Unknown'),
        'capabilities': capabilities,
        'driver_type': chipset_info.get('driver_type', 'Generic VCP'),
        'known_issues': chipset_info.get('known_issues', [])
    }
    
    return result


def format_enhanced_device_report(enhanced_info: Dict) -> str:
    """
    Format enhanced device information into a readable report.
    
    Args:
        enhanced_info: Enhanced device information from get_enhanced_device_info()
        
    Returns:
        str: Formatted device report
    """
    report = []
    basic = enhanced_info.get('basic_info', {})
    chipset = enhanced_info.get('chipset_info', {})
    usb = enhanced_info.get('usb_descriptor', {})
    amt_info = enhanced_info.get('amt_info', {})
    is_intel_amt = enhanced_info.get('is_intel_amt', False)
    methods = enhanced_info.get('identification_method', [])
    
    # Handle Intel AMT devices specially
    if is_intel_amt and amt_info:
        return format_amt_device_report(amt_info, include_status=True)
    
    # Device identification section
    report.append("===== DEVICE IDENTIFICATION =====")
    if basic.get('name') != 'Unknown Device':
        report.append(f"Device: {basic['name']}")
        report.append(f"Description: {basic['description']}")
        report.append(f"Manufacturer: {basic['manufacturer']}")
        if 'confidence' in basic:
            report.append(f"Confidence: {basic['confidence']:.0%}")
    else:
        report.append("Could not identify device type specifically.")
        report.append("This appears to be a generic serial device or uses an unknown chipset.")
    
    # USB descriptor information
    if usb:
        report.append("\n===== USB DESCRIPTOR INFORMATION =====")
        if usb.get('manufacturer') and usb['manufacturer'] != 'Unknown':
            report.append(f"USB Manufacturer: {usb['manufacturer']}")
        if usb.get('product') and usb['product'] != 'Unknown':
            report.append(f"USB Product: {usb['product']}")
        if usb.get('serial_number') and usb['serial_number'] != 'Unknown':
            report.append(f"Serial Number: {usb['serial_number']}")
        if usb.get('device_class') and usb['device_class'] != 'Unknown':
            report.append(f"Device Class: {usb['device_class']}")
    
    # Intel AMT information (for Intel devices without full AMT detection)
    if is_intel_amt and not amt_info:
        report.append("\n===== INTEL AMT INFORMATION =====")
        report.append("This appears to be an Intel device with potential AMT capabilities.")
        report.append("Intel AMT (Active Management Technology) provides:")
        report.append("• Remote management capabilities")
        report.append("• Serial-over-LAN (SOL) functionality")
        report.append("• Out-of-band management")
        report.append("• BIOS/UEFI level access")
        report.append("\nNote: AMT must be enabled and configured in BIOS/UEFI settings.")
    
    # Chipset capabilities
    if chipset:
        report.append("\n===== CHIPSET INFORMATION =====")
        report.append(f"Chipset Family: {chipset['chipset_family']}")
        report.append(f"Chipset Variant: {chipset['chipset_variant']}")
        report.append(f"UART Channels: {chipset['uart_channels']}")
        report.append(f"Max Baudrate: {chipset['max_baudrate']:,} bps")
        if chipset['gpio_pins'] > 0:
            report.append(f"GPIO Pins: {chipset['gpio_pins']}")
        if chipset['features']:
            report.append(f"Features: {', '.join(chipset['features'])}")
        if chipset['known_issues']:
            report.append(f"Known Issues: {'; '.join(chipset['known_issues'])}")
    
    # Identification methods
    if methods:
        report.append(f"\n===== IDENTIFICATION METHODS =====")
        for method in methods:
            report.append(f"✓ {method}")
    
    return "\n".join(report)


def extract_vid_pid_from_hwid(hwid: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract VID and PID from hardware ID string using multiple patterns.
    
    Args:
        hwid: Hardware ID string
        
    Returns:
        tuple: (VID, PID) as integers or (None, None) if not found
    """
    if not hwid:
        return None, None
    
    hwid_upper = hwid.upper()
    
    # Pattern 1: VID_xxxx&PID_xxxx (Windows USB devices)
    usb_pattern = re.search(r'VID_([0-9A-F]{4}).*?PID_([0-9A-F]{4})', hwid_upper)
    if usb_pattern:
        try:
            vid = int(usb_pattern.group(1), 16)
            pid = int(usb_pattern.group(2), 16)
            return vid, pid
        except ValueError:
            pass
    
    # Pattern 2: USB\VID_xxxx&PID_xxxx (Alternative Windows format)
    usb_alt_pattern = re.search(r'USB\\VID_([0-9A-F]{4})&PID_([0-9A-F]{4})', hwid_upper)
    if usb_alt_pattern:
        try:
            vid = int(usb_alt_pattern.group(1), 16)
            pid = int(usb_alt_pattern.group(2), 16)
            return vid, pid
        except ValueError:
            pass
    
    # Pattern 3: xxxx:xxxx format (Linux style)
    colon_pattern = re.search(r'([0-9A-F]{4}):([0-9A-F]{4})', hwid_upper)
    if colon_pattern:
        try:
            vid = int(colon_pattern.group(1), 16)
            pid = int(colon_pattern.group(2), 16)
            return vid, pid
        except ValueError:
            pass
    
    # Pattern 4: Extract from PCI device IDs (for Intel AMT)
    pci_pattern = re.search(r'PCI\\VEN_([0-9A-F]{4})&DEV_([0-9A-F]{4})', hwid_upper)
    if pci_pattern:
        try:
            vid = int(pci_pattern.group(1), 16)
            pid = int(pci_pattern.group(2), 16)
            return vid, pid
        except ValueError:
            pass
    
    return None, None


def extract_vid_pid_from_description(description: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Try to extract VID/PID from device description using known patterns.
    
    Args:
        description: Device description string
        
    Returns:
        tuple: (VID, PID) as integers or (None, None) if not found
    """
    if not description:
        return None, None
    
    desc_lower = description.lower()
    
    # Intel AMT SOL devices
    if 'intel' in desc_lower and ('amt' in desc_lower or 'sol' in desc_lower or 'active management' in desc_lower):
        return 0x8086, 0x9D3D  # Default Intel AMT SOL VID:PID
    
    # FTDI devices
    if 'ftdi' in desc_lower or 'ft232' in desc_lower:
        if 'ft232h' in desc_lower:
            return 0x0403, 0x6014
        elif 'ft2232' in desc_lower:
            return 0x0403, 0x6010
        else:
            return 0x0403, 0x6001  # Default FT232R
    
    # Silicon Labs
    if 'silicon labs' in desc_lower or 'cp210' in desc_lower:
        return 0x10C4, 0xEA60
    
    # Prolific
    if 'prolific' in desc_lower or 'pl2303' in desc_lower:
        return 0x067B, 0x2303
    
    # WCH CH340
    if 'ch340' in desc_lower or 'ch341' in desc_lower:
        return 0x1A86, 0x7523
    
    return None, None


def get_enhanced_vid_pid(port_info: Dict) -> Tuple[Optional[int], Optional[int]]:
    """
    Get VID/PID using multiple extraction methods with fallbacks.
    
    Args:
        port_info: Port information dictionary
        
    Returns:
        tuple: (VID, PID) as integers or (None, None) if not found
    """
    # Method 1: Direct VID/PID from pyserial
    if port_info.get("vid") is not None and port_info.get("pid") is not None:
        return port_info["vid"], port_info["pid"]
    
    # Method 2: Extract from hardware ID
    if port_info.get("hwid"):
        vid, pid = extract_vid_pid_from_hwid(port_info["hwid"])
        if vid is not None and pid is not None:
            return vid, pid
    
    # Method 3: Extract from description patterns
    if port_info.get("description"):
        vid, pid = extract_vid_pid_from_description(port_info["description"])
        if vid is not None and pid is not None:
            return vid, pid
    
    # Method 4: Windows-specific registry lookup
    port_device = port_info.get("device") or port_info.get("port_name") or port_info.get("name")
    if platform.system() == "Windows" and port_device:
        vid, pid = _windows_registry_vid_pid_lookup(port_device)
        if vid is not None and pid is not None:
            return vid, pid
    
    return None, None


def _windows_registry_vid_pid_lookup(port_name: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Look up VID/PID from Windows registry for a specific COM port.
    
    Args:
        port_name: COM port name (e.g., 'COM3')
        
    Returns:
        tuple: (VID, PID) as integers or (None, None) if not found
    """
    if not winreg:
        return None, None
    
    try:
        import wmi
        c = wmi.WMI()
        
        # Find the COM port in WMI
        for port_device in c.Win32_SerialPort():
            if port_device.DeviceID == port_name:
                pnp_device_id = port_device.PNPDeviceID
                if pnp_device_id:
                    return extract_vid_pid_from_hwid(pnp_device_id)
                    
        # Alternative: Look through PnP entities
        for device in c.Win32_PnPEntity():
            if device.Name and port_name.lower() in device.Name.lower():
                if device.DeviceID:
                    return extract_vid_pid_from_hwid(device.DeviceID)
                    
    except ImportError:
        pass
    except Exception:
        pass
    
    return None, None


def detect_intel_amt_sol_ports() -> List[Dict]:
    """
    Detect Intel AMT SOL (Serial-over-LAN) COM ports using system-specific methods.
    
    Returns:
        List[Dict]: List of detected AMT SOL port information
    """
    amt_ports = []
    system = platform.system()
    
    try:
        if system == "Windows":
            amt_ports = _detect_windows_amt_sol_ports()
        elif system == "Linux":
            amt_ports = _detect_linux_amt_sol_ports()
        elif system == "Darwin":  # macOS
            amt_ports = _detect_macos_amt_sol_ports()
    except Exception:
        pass
    
    return amt_ports


def _detect_windows_amt_sol_ports() -> List[Dict]:
    """Detect Intel AMT SOL ports on Windows using registry and WMI."""
    amt_ports = []
    
    if not winreg:
        return amt_ports
    
    try:
        import wmi
        c = wmi.WMI()
        
        # Search for Intel AMT devices in PnP entities
        for device in c.Win32_PnPEntity():
            if device.Name and device.DeviceID:
                name = device.Name.lower()
                device_id = device.DeviceID.lower()
                
                # Check for Intel AMT SOL patterns
                amt_patterns = [
                    "intel",
                    "active management",
                    "amt", 
                    "serial over lan",
                    "sol"
                ]
                
                if any(pattern in name for pattern in amt_patterns) or any(pattern in device_id for pattern in amt_patterns):
                    # Check if it's a COM port
                    for port_device in c.Win32_SerialPort():
                        if port_device.PNPDeviceID and device.DeviceID in port_device.PNPDeviceID:
                            amt_info = {
                                'port_name': port_device.DeviceID,
                                'device_name': device.Name,
                                'device_id': device.DeviceID,
                                'manufacturer': device.Manufacturer or 'Intel Corporation',
                                'driver_version': device.DriverVersion,
                                'driver_date': device.DriverDate,
                                'status': device.Status,
                                'amt_type': _classify_amt_device(device.Name)
                            }
                            amt_ports.append(amt_info)
                            
    except ImportError:
        pass
    
    return amt_ports


def _detect_linux_amt_sol_ports() -> List[Dict]:
    """Detect Intel AMT SOL ports on Linux using sysfs and dmesg."""
    amt_ports = []
    
    try:
        # Check dmesg for Intel AMT messages
        result = subprocess.run(['dmesg'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            dmesg_output = result.stdout.lower()
            
            # Look for Intel AMT/MEI related messages
            if 'intel' in dmesg_output and any(term in dmesg_output for term in ['amt', 'mei', 'sol']):
                # Parse for COM port assignments
                import glob
                for tty_path in glob.glob('/sys/class/tty/ttyS*'):
                    try:
                        device_path = f"{tty_path}/device"
                        if os.path.exists(device_path):
                            # Read device information
                            uevent_path = f"{device_path}/uevent"
                            if os.path.exists(uevent_path):
                                with open(uevent_path, 'r') as f:
                                    uevent_data = f.read().lower()
                                    if 'intel' in uevent_data:
                                        port_name = os.path.basename(tty_path)
                                        amt_info = {
                                            'port_name': f'/dev/{port_name}',
                                            'device_name': 'Intel AMT SOL',
                                            'manufacturer': 'Intel Corporation',
                                            'amt_type': 'SOL',
                                            'sys_path': tty_path
                                        }
                                        amt_ports.append(amt_info)
                    except (OSError, IOError):
                        continue
                        
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return amt_ports


def _detect_macos_amt_sol_ports() -> List[Dict]:
    """Detect Intel AMT SOL ports on macOS using system information."""
    amt_ports = []
    
    try:
        # Check system profiler for Intel devices
        result = subprocess.run(['system_profiler', 'SPHardwareDataType', 'SPSerialATADataType'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            output = result.stdout.lower()
            if 'intel' in output:
                # Look for serial devices that might be AMT SOL
                serial_result = subprocess.run(['ls', '/dev/cu.*'], 
                                             capture_output=True, text=True, timeout=5)
                if serial_result.returncode == 0:
                    for line in serial_result.stdout.split('\n'):
                        if line.strip() and 'intel' in line.lower():
                            amt_info = {
                                'port_name': line.strip(),
                                'device_name': 'Intel AMT SOL',
                                'manufacturer': 'Intel Corporation',
                                'amt_type': 'SOL'
                            }
                            amt_ports.append(amt_info)
                            
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return amt_ports


def _classify_amt_device(device_name: str) -> str:
    """Classify the type of Intel AMT device based on device name."""
    name_lower = device_name.lower()
    
    if 'sol' in name_lower or 'serial over lan' in name_lower:
        return 'SOL'
    elif 'amt' in name_lower or 'active management' in name_lower:
        return 'AMT_Management'
    elif 'mei' in name_lower:
        return 'MEI_Interface'
    else:
        return 'Intel_Management'


def get_amt_device_status(port_name: str) -> Dict:
    """
    Get Intel AMT device status and configuration information.
    
    Args:
        port_name: COM port name (e.g., 'COM3', '/dev/ttyS0')
        
    Returns:
        dict: AMT device status information
    """
    status_info = {
        'port_available': False,
        'amt_enabled': False,
        'sol_enabled': False,
        'network_connectivity': False,
        'firmware_version': 'Unknown',
        'recommendations': []
    }
    
    try:
        # Test port availability
        import serial
        with serial.Serial(port_name, 115200, timeout=1) as ser:
            status_info['port_available'] = True
            
            # Try to detect AMT SOL activity
            ser.write(b'\r\n')
            response = ser.read(100)
            if response:
                status_info['sol_enabled'] = True
                
    except serial.SerialException:
        status_info['recommendations'].append('Port is not accessible - check AMT configuration')
    except Exception:
        status_info['recommendations'].append('Unable to test port connectivity')
    
    # Add general AMT recommendations
    if not status_info['port_available']:
        status_info['recommendations'].extend([
            'Enable Intel AMT in BIOS/UEFI settings',
            'Configure AMT network settings in MEBx',
            'Install Intel AMT drivers',
            'Verify AMT firmware is up to date'
        ])
    
    return status_info


def format_amt_device_report(amt_info: Dict, include_status: bool = True) -> str:
    """
    Format Intel AMT device information into a comprehensive report.
    
    Args:
        amt_info: AMT device information
        include_status: Whether to include status check
        
    Returns:
        str: Formatted AMT device report
    """
    report = []
    
    report.append("===== INTEL AMT DEVICE IDENTIFICATION =====")
    report.append(f"Device: {amt_info.get('device_name', 'Intel AMT Device')}")
    report.append(f"Port: {amt_info.get('port_name', 'Unknown')}")
    report.append(f"Manufacturer: {amt_info.get('manufacturer', 'Intel Corporation')}")
    report.append(f"AMT Type: {amt_info.get('amt_type', 'Unknown')}")
    
    if amt_info.get('driver_version'):
        report.append(f"Driver Version: {amt_info['driver_version']}")
    if amt_info.get('driver_date'):
        report.append(f"Driver Date: {amt_info['driver_date']}")
    
    report.append("\n===== AMT SOL CAPABILITIES =====")
    report.append("• Remote serial console access")
    report.append("• Out-of-band management")
    report.append("• BIOS/UEFI level access")
    report.append("• Network-independent operation")
    report.append("• Default settings: 115200 baud, 8N1, no flow control")
    
    if include_status and amt_info.get('port_name'):
        status = get_amt_device_status(amt_info['port_name'])
        
        report.append("\n===== AMT STATUS =====")
        report.append(f"Port Available: {'Yes' if status['port_available'] else 'No'}")
        report.append(f"SOL Enabled: {'Yes' if status['sol_enabled'] else 'Unknown'}")
        
        if status['recommendations']:
            report.append("\n===== RECOMMENDATIONS =====")
            for rec in status['recommendations']:
                report.append(f"• {rec}")
    
    report.append("\n===== AMT CONFIGURATION NOTES =====")
    report.append("• Access MEBx during boot (Ctrl+P) to configure AMT")
    report.append("• Ensure AMT is provisioned and enabled")
    report.append("• Configure network settings for remote access")
    report.append("• Set SOL/IDER redirection options")
    report.append("• Use Intel AMT tools or third-party management software")
    
    return "\n".join(report)