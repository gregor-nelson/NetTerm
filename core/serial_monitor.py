"""
Core Serial Monitor module for handling serial communication.
"""
import serial
import threading
import time
from datetime import datetime

class SerialMonitor:
    def __init__(self, port, baudrate=9600, timeout=1, 
                 logfile=None, timestamp=False, hex_display=False,
                 bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, 
                 stopbits=serial.STOPBITS_ONE, dtr_enable=None, rts_enable=None,
                 termination='\r', auto_termination=True, encoding='utf-8', debug=False):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.logfile = logfile
        self.timestamp = timestamp
        self.hex_display = hex_display
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.dtr_enable = dtr_enable
        self.rts_enable = rts_enable
        self.termination = termination
        self.auto_termination = auto_termination  # Flag to control auto-termination
        self.encoding = encoding
        self.debug = debug
        
        self.ser = None
        self.stop_event = threading.Event()
        self.log_file_handle = None
        self.serial_lock = threading.Lock()
        self.rx_buffer = bytearray()  # Buffer for incoming data

    def open_connection(self):
        try:
            with self.serial_lock:
                self.ser = serial.Serial()
                self.ser.port = self.port
                self.ser.baudrate = self.baudrate
                self.ser.timeout = self.timeout
                self.ser.bytesize = self.bytesize
                self.ser.parity = self.parity
                self.ser.stopbits = self.stopbits
                self.ser.open()
                
                if self.dtr_enable is not None:
                    self.ser.dtr = self.dtr_enable
                if self.rts_enable is not None:
                    self.ser.rts = self.rts_enable
                
            if self.logfile:
                self.log_file_handle = open(self.logfile, 'a')
            return True
        except serial.SerialException as e:
            print(f"Error opening port {self.port}: {e}")
            return False

    def close_connection(self):
        with self.serial_lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
        if self.log_file_handle:
            self.log_file_handle.close()
            self.log_file_handle = None

    def read_serial(self):
        while not self.stop_event.is_set():
            try:
                with self.serial_lock:
                    if self.ser and self.ser.is_open:
                        data = self.ser.read(self.ser.in_waiting or 1)
                        if data:
                            return data
                time.sleep(0.01)
            except serial.SerialException as e:
                print(f"Serial error: {e}")
                time.sleep(1)
        return None

    def send_data(self, data):
        with self.serial_lock:
            if self.ser and self.ser.is_open:
                try:
                    # Only add termination if auto_termination is enabled
                    if self.auto_termination and self.termination and not data.endswith(self.termination):
                        data += self.termination
                    bytes_data = data.encode(self.encoding, errors='replace')
                    self.ser.write(bytes_data)
                    self.ser.flush()
                    if self.debug:
                        print(f"Debug: Sent {len(bytes_data)} bytes: {bytes_data!r}")
                    if self.log_file_handle:
                        self.log_file_handle.write(f"[TX] {data}\n")
                        self.log_file_handle.flush()
                    return bytes_data
                except serial.SerialException as e:
                    print(f"Error sending data: {e}")
                    return None
        return None

    def send_key(self, key):
        """Send a single key without any processing or termination"""
        with self.serial_lock:
            if self.ser and self.ser.is_open:
                try:
                    # Map special keys to their escape sequences
                    key_map = {
                        'Enter': '\r',
                        'Return': '\r',
                        'Escape': '\x1b',
                        'Esc': '\x1b',
                        'Tab': '\t',
                        'Backspace': '\b',
                    }
                    
                    # Get the key sequence
                    key_sequence = key_map.get(key, key)
                    bytes_data = key_sequence.encode(self.encoding, errors='replace')
                    
                    self.ser.write(bytes_data)
                    self.ser.flush()
                    
                    if self.debug:
                        print(f"Debug: Sent key {key} as bytes: {bytes_data!r}")
                    if self.log_file_handle:
                        self.log_file_handle.write(f"[KEY] {key}\n")
                        self.log_file_handle.flush()
                    return bytes_data
                except serial.SerialException as e:
                    print(f"Error sending key: {e}")
                    return None
        return None

    def start(self):
        return self.open_connection()

    def stop(self):
        self.stop_event.set()
        self.close_connection()