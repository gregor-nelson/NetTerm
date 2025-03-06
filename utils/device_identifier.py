"""
Device identification utilities for serial ports.
"""
import re


# Dictionary of VID:PID to device information
KNOWN_DEVICES = {
    # FTDI Devices
    "0403:6001": {
        "name": "FTDI FT232 USB-Serial Adapter",
        "description": "Common USB to Serial adapter chip used in many devices",
        "manufacturer": "FTDI"
    },
    "0403:6010": {
        "name": "FTDI FT2232 Dual USB-Serial Adapter",
        "description": "Dual channel USB to Serial adapter",
        "manufacturer": "FTDI"
    },
    "0403:6014": {
        "name": "FTDI FT232H USB-Serial Adapter",
        "description": "High-speed USB to Serial/FIFO adapter",
        "manufacturer": "FTDI"
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
        "manufacturer": "STMicroelectronics"
    },
    "0483:5740": {
        "name": "STM32 Virtual COM Port",
        "description": "STM32 microcontroller with USB",
        "manufacturer": "STMicroelectronics"
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
            "manufacturer": "Raspberry Pi Foundation"
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