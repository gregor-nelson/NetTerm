"""
Thread module for handling serial communication in a separate thread.
"""
import time
from PyQt6.QtCore import QThread, pyqtSignal
from core.serial_monitor import SerialMonitor  # Updated import path

class SerialThread(QThread):
    data_received = pyqtSignal(str)  # Signal to emit complete lines as strings
    error_occurred = pyqtSignal(str)

    def __init__(self, monitor):
        super().__init__()
        self.monitor = monitor
        self.buffer = bytearray()

    def run(self):
        while not self.monitor.stop_event.is_set():
            data = self.monitor.read_serial()
            if data:
                self.buffer.extend(data)
                # Check for line terminators (\n, \r, or \r\n)
                while True:
                    # Look for common line endings
                    line_endings = [b'\r\n', b'\n', b'\r']
                    earliest_end = -1
                    earliest_ending = None
                    
                    for ending in line_endings:
                        pos = self.buffer.find(ending)
                        if pos != -1 and (earliest_end == -1 or pos < earliest_end):
                            earliest_end = pos
                            earliest_ending = ending
                    
                    if earliest_end == -1:
                        break  # No complete line yet, wait for more data
                    
                    # Extract the line
                    line = self.buffer[:earliest_end]
                    self.buffer = self.buffer[earliest_end + len(earliest_ending):]
                    
                    try:
                        line_text = line.decode(self.monitor.encoding, errors='replace').strip()
                        if line_text:  # Only emit non-empty lines
                            self.data_received.emit(line_text)
                    except UnicodeDecodeError:
                        line_text = ' '.join(f'{b:02X}' for b in line)
                        self.data_received.emit(line_text)
            elif self.monitor.stop_event.is_set():
                break
            else:
                # Sleep to prevent CPU spinning if no data
                time.sleep(0.2)