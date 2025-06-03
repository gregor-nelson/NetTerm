"""
Serial Port Monitoring module for real-time statistics and data flow observation.
"""
import time
import threading
from datetime import datetime, timedelta
import serial
from PyQt6.QtCore import QObject, pyqtSignal


class SerialPortMonitor(QObject):
    """
    Class for monitoring a serial port and collecting statistics.
    """
    # Signals
    stats_updated = pyqtSignal(dict)  # Emits updated port statistics
    data_received = pyqtSignal(bytes)  # Emits raw data received
    error_occurred = pyqtSignal(str)  # Emits error messages
    
    def __init__(self, port_name, baudrate=9600):
        """
        Initialize the serial port monitor.
        
        Args:
            port_name: Serial port name
            baudrate: Baud rate for monitoring
        """
        super().__init__()
        
        self.port_name = port_name
        self.baudrate = baudrate
        
        # Statistics
        self.stats = {
            "rx_bytes": 0,
            "tx_bytes": 0,
            "rx_rate": 0.0,  # bytes per second
            "tx_rate": 0.0,  # bytes per second
            "errors": 0,
            "start_time": None,
            "running_time": 0.0
        }
        
        # Rate calculation windows
        self.rx_window = []  # List of (timestamp, bytes) tuples
        self.tx_window = []  # List of (timestamp, bytes) tuples
        self.window_size = 10  # seconds for rate calculation
        
        # Operation flags
        self.running = False
        self.stop_event = threading.Event()
        
        # Serial port
        self.ser = None
        self.monitor_thread = None
    
    def start(self):
        """Start monitoring the serial port."""
        if self.running:
            return True
            
        try:
            # Open the port in non-exclusive mode if possible
            self.ser = serial.Serial()
            self.ser.port = self.port_name
            self.ser.baudrate = self.baudrate
            self.ser.timeout = 0.1
            
            # Try to open without exclusive access if supported
            try:
                # This works on Linux/Unix where the serial port can be opened in non-exclusive mode
                if hasattr(serial, 'TIOCEXCL'):
                    import fcntl
                    self.ser.open()
                    fcntl.ioctl(self.ser.fileno(), ~serial.TIOCEXCL)
                else:
                    self.ser.open()
            except:
                # Fallback to standard open
                self.ser.open()
            
            # Reset stats
            self.stats = {
                "rx_bytes": 0,
                "tx_bytes": 0,
                "rx_rate": 0.0,
                "tx_rate": 0.0,
                "errors": 0,
                "start_time": datetime.now(),
                "running_time": 0.0
            }
            
            self.rx_window = []
            self.tx_window = []
            
            # Start the monitor thread
            self.running = True
            self.stop_event.clear()
            self.monitor_thread = threading.Thread(target=self._monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            return True
            
        except serial.SerialException as e:
            self.error_occurred.emit(f"Error opening {self.port_name}: {str(e)}")
            self.running = False
            return False
    
    def stop(self):
        """Stop monitoring the serial port."""
        if not self.running:
            return
            
        self.running = False
        self.stop_event.set()
        
        # Wait for thread to exit
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        
        # Close the port
        if self.ser and self.ser.is_open:
            self.ser.close()
    
    def _monitor_loop(self):
        """Main monitoring loop running in a separate thread."""
        last_stats_update = time.time()
        
        while self.running and not self.stop_event.is_set():
            try:
                # Try to read data if available
                if self.ser and self.ser.is_open:
                    # Check for incoming data
                    if self.ser.in_waiting > 0:
                        data = self.ser.read(self.ser.in_waiting)
                        if data:
                            # Update statistics
                            self.stats["rx_bytes"] += len(data)
                            now = time.time()
                            self.rx_window.append((now, len(data)))
                            
                            # Emit the data
                            self.data_received.emit(data)
                    
                    # Update running time and rates periodically
                    now = time.time()
                    if now - last_stats_update >= 1.0:  # Update stats every second
                        self._update_rates(now)
                        self.stats["running_time"] = (datetime.now() - self.stats["start_time"]).total_seconds()
                        
                        # Emit updated stats
                        self.stats_updated.emit(self.stats.copy())
                        last_stats_update = now
                
                # Short sleep to prevent CPU thrashing
                time.sleep(0.05)
                
            except serial.SerialException as e:
                self.stats["errors"] += 1
                self.error_occurred.emit(f"Serial error: {str(e)}")
                # Attempt to reopen the port
                self._attempt_reopen()
            except Exception as e:
                self.stats["errors"] += 1
                self.error_occurred.emit(f"Monitor error: {str(e)}")
        
        # Ensure port is closed on exit
        if self.ser and self.ser.is_open:
            self.ser.close()
    
    def _update_rates(self, now):
        """
        Update RX and TX rates based on windowed data.
        
        Args:
            now: Current timestamp
        """
        # Remove old data points outside the window
        window_start = now - self.window_size
        self.rx_window = [(ts, sz) for ts, sz in self.rx_window if ts >= window_start]
        self.tx_window = [(ts, sz) for ts, sz in self.tx_window if ts >= window_start]
        
        # Calculate rates
        if self.rx_window:
            total_rx_bytes = sum(sz for _, sz in self.rx_window)
            oldest_ts = min(ts for ts, _ in self.rx_window)
            if now > oldest_ts:
                time_span = now - oldest_ts
                self.stats["rx_rate"] = total_rx_bytes / time_span
            else:
                self.stats["rx_rate"] = 0.0
        else:
            self.stats["rx_rate"] = 0.0
        
        if self.tx_window:
            total_tx_bytes = sum(sz for _, sz in self.tx_window)
            oldest_ts = min(ts for ts, _ in self.tx_window)
            if now > oldest_ts:
                time_span = now - oldest_ts
                self.stats["tx_rate"] = total_tx_bytes / time_span
            else:
                self.stats["tx_rate"] = 0.0
        else:
            self.stats["tx_rate"] = 0.0
    
    def _attempt_reopen(self):
        """Attempt to reopen the serial port after an error."""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            time.sleep(0.5)  # Wait before reopening
            
            if self.ser:
                self.ser.open()
                
        except Exception:
            # Just log the error once and continue
            pass
    
    def send_data(self, data):
        """
        Send data to the serial port.
        
        Args:
            data: Bytes or string to send
            
        Returns:
            bool: Success status
        """
        if not self.running or not self.ser or not self.ser.is_open:
            return False
            
        try:
            # Convert string to bytes if needed
            if isinstance(data, str):
                data = data.encode('utf-8')
                
            # Send the data
            bytes_sent = self.ser.write(data)
            
            # Update statistics
            if bytes_sent > 0:
                self.stats["tx_bytes"] += bytes_sent
                now = time.time()
                self.tx_window.append((now, bytes_sent))
            
            return bytes_sent > 0
            
        except Exception as e:
            self.stats["errors"] += 1
            self.error_occurred.emit(f"Send error: {str(e)}")
            return False
    
    def get_formatted_stats(self):
        """
        Get formatted statistics as a string.
        
        Returns:
            str: Formatted statistics string
        """
        if not self.stats["start_time"]:
            return "Not monitoring"
            
        # Format rates
        rx_rate = self.stats["rx_rate"]
        tx_rate = self.stats["tx_rate"]
        
        # Choose appropriate units
        if rx_rate < 1024:
            rx_rate_str = f"{rx_rate:.1f} B/s"
        else:
            rx_rate_str = f"{rx_rate/1024:.1f} KB/s"
            
        if tx_rate < 1024:
            tx_rate_str = f"{tx_rate:.1f} B/s"
        else:
            tx_rate_str = f"{tx_rate/1024:.1f} KB/s"
            
        # Format running time
        seconds = int(self.stats["running_time"])
        running_time = str(timedelta(seconds=seconds))
        
        # Format the statistics string
        stats_str = f"Running time: {running_time}\n"
        stats_str += f"RX: {self.stats['rx_bytes']} bytes (Rate: {rx_rate_str})\n"
        stats_str += f"TX: {self.stats['tx_bytes']} bytes (Rate: {tx_rate_str})\n"
        stats_str += f"Errors: {self.stats['errors']}"
        
        return stats_str