"""
Serial Port Scanner tab UI component.
"""
import os
import csv
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QLabel, QHeaderView,
                           QGroupBox, QComboBox, QAbstractItemView, QTextEdit,
                           QFileDialog, QSplitter, QMessageBox, QDialog, QCheckBox,QApplication,
                           QDialogButtonBox, QLineEdit, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QTextCursor

from core.port_monitor import SerialPortMonitor
from utils.device_identifier import (identify_device_by_vid_pid, 
                                   identify_device_by_description,
                                   get_device_driver_recommendations,
                                   get_enhanced_device_info,
                                   format_enhanced_device_report,
                                   get_enhanced_vid_pid)


class SerialPortScannerTab(QWidget):
    """Serial Port Scanner tab UI component."""
    
    # Define signals for communication with parent
    status_message = pyqtSignal(str, int)  # message, timeout
    error_occurred = pyqtSignal(str)
    
    def __init__(self, ui_scaler, parent=None):
        """
        Initialize the Serial Port Scanner tab component.
        
        Args:
            ui_scaler: UIScaler instance for responsive UI
            parent: Parent widget
        """
        super().__init__(parent)
        self.scaler = ui_scaler
        
        # Initialize variables
        self.port_info = {}  # Dictionary to store port information
        self.monitoring = False  # Flag to indicate if monitoring is active
        self.port_monitor = None  # Port monitor instance
        self.monitored_port = None  # Currently monitored port
        
        # Setup UI
        self.init_ui()
        self.setup_fonts()
        
        # Create timer for periodic scanning
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.scan_ports)
        
        # Create timer for monitor updates
        self.monitor_update_timer = QTimer()
        self.monitor_update_timer.timeout.connect(self.update_monitor_display)
        
        # Initial scan
        self.scan_ports()
    
    def init_ui(self):
        """Initialize the Serial Port Scanner tab UI."""
        scanner_layout = QVBoxLayout(self)
        self.scaler.spacing(scanner_layout, self.scaler.SPACING_MEDIUM)
        self.scaler.margins(scanner_layout, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE)
        
        # Control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        self.scaler.spacing(control_layout, self.scaler.SPACING_SMALL)
        
        # Scan button
        self.scan_button = QPushButton("Scan Ports")
        self.scan_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        self.scan_button.clicked.connect(self.scan_ports)
        
        # Remove custom styling - use theme system
        control_layout.addWidget(self.scan_button)
        
        # Auto-refresh toggle
        self.auto_refresh_toggle = QPushButton("Auto Refresh")
        self.auto_refresh_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.auto_refresh_toggle.setCheckable(True)
        self.auto_refresh_toggle.clicked.connect(self.toggle_auto_refresh)
        control_layout.addWidget(self.auto_refresh_toggle)
        
        # Refresh interval
        refresh_interval_label = QLabel("Refresh Interval:")
        refresh_interval_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        control_layout.addWidget(refresh_interval_label)
        
        self.refresh_interval_combo = QComboBox()
        self.refresh_interval_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.refresh_interval_combo.addItems(["1 second", "2 seconds", "5 seconds", "10 seconds"])
        self.refresh_interval_combo.setCurrentIndex(1)  # Default to 2 seconds
        control_layout.addWidget(self.refresh_interval_combo)
        
        # Port test toggle
        self.test_ports_toggle = QPushButton("Test Port Availability")
        self.test_ports_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.test_ports_toggle.setCheckable(True)
        self.test_ports_toggle.clicked.connect(self.toggle_port_testing)
        control_layout.addWidget(self.test_ports_toggle)
        
        # Export button
        self.export_button = QPushButton("Export")
        self.export_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.export_button.clicked.connect(self.export_port_info)
        control_layout.addWidget(self.export_button)
        
        # Add spacer
        control_layout.addStretch()
        
        scanner_layout.addWidget(control_panel)
        
        # Main content area with splitter for flexible layout
        content_splitter = QSplitter(Qt.Orientation.Vertical)
        content_splitter.setChildrenCollapsible(False)
        
        # Ports table section
        ports_group = QGroupBox("Available Serial Ports")
        ports_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        ports_layout = QVBoxLayout(ports_group)
        self.scaler.spacing(ports_layout, self.scaler.SPACING_SMALL)
        
        self.ports_table = QTableWidget(0, 7)  # 7 columns
        self.ports_table.setHorizontalHeaderLabels([
            "Port", "Description", "Manufacturer", "VID:PID", 
            "Status", "Location", "Serial Number"
        ])
        
        # Configure table properties
        self.ports_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.ports_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.ports_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.ports_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.ports_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.ports_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.ports_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        self.ports_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.ports_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        ports_layout.addWidget(self.ports_table)
        
        # Button row for port actions
        port_actions_layout = QHBoxLayout()
        self.scaler.spacing(port_actions_layout, self.scaler.SPACING_SMALL)
        
        self.identify_device_button = QPushButton("Identify Selected Device")
        self.identify_device_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.identify_device_button.clicked.connect(self.identify_selected_device)
        port_actions_layout.addWidget(self.identify_device_button)
        
        self.autodetect_speed_button = QPushButton("Auto-Detect Speed")
        self.autodetect_speed_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.autodetect_speed_button.clicked.connect(self.autodetect_port_speed)
        port_actions_layout.addWidget(self.autodetect_speed_button)
        
        self.monitor_button = QPushButton("Monitor Port")
        self.monitor_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        self.monitor_button.setCheckable(True)
        self.monitor_button.clicked.connect(self.toggle_port_monitoring)
        port_actions_layout.addWidget(self.monitor_button)
        
        port_actions_layout.addStretch()
        
        ports_layout.addLayout(port_actions_layout)
        
        # Add the ports group to the content splitter
        content_splitter.addWidget(ports_group)
        
        # Bottom section with details and monitoring
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Details section for selected port
        details_group = QGroupBox("Port Details")
        details_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        details_layout = QVBoxLayout(details_group)
        self.scaler.spacing(details_layout, self.scaler.SPACING_SMALL)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setText("Select a port to view detailed information")
        details_layout.addWidget(self.details_text)
        
        # Connect selection changed signal
        self.ports_table.itemSelectionChanged.connect(self.update_port_details)
        
        # Test connection button for selected port
        test_layout = QHBoxLayout()
        self.scaler.spacing(test_layout, self.scaler.SPACING_SMALL)
        
        self.test_selected_button = QPushButton("Test Selected Port")
        self.test_selected_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.test_selected_button.clicked.connect(self.test_selected_port)
        test_layout.addWidget(self.test_selected_button)
        
        self.refresh_selected_button = QPushButton("Refresh Selected Port")
        self.refresh_selected_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.refresh_selected_button.clicked.connect(self.refresh_selected_port)
        test_layout.addWidget(self.refresh_selected_button)
        
        test_layout.addStretch()
        
        details_layout.addLayout(test_layout)
        
        # Add the details group to the bottom splitter
        bottom_splitter.addWidget(details_group)
        
        # Port Monitor section
        monitor_group = QGroupBox("Port Monitor")
        monitor_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        monitor_layout = QVBoxLayout(monitor_group)
        self.scaler.spacing(monitor_layout, self.scaler.SPACING_SMALL)
        
        # Monitor display
        self.monitor_text = QTextEdit()
        self.monitor_text.setReadOnly(True)
        self.monitor_text.setFont(self.scaler.get_code_font())
        self.monitor_text.setText("Select a port and click 'Monitor Port' to start monitoring")
        monitor_layout.addWidget(self.monitor_text)
        
        # Monitor controls
        monitor_controls_layout = QHBoxLayout()
        self.scaler.spacing(monitor_controls_layout, self.scaler.SPACING_SMALL)
        
        monitor_baudrate_label = QLabel("Baudrate:")
        monitor_baudrate_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        monitor_controls_layout.addWidget(monitor_baudrate_label)
        
        self.monitor_baudrate_combo = QComboBox()
        self.monitor_baudrate_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.monitor_baudrate_combo.addItems(['300', '1200', '2400', '4800', '9600', '19200', 
                                           '38400', '57600', '115200', '230400'])
        self.monitor_baudrate_combo.setCurrentText('9600')
        monitor_controls_layout.addWidget(self.monitor_baudrate_combo)
        
        self.clear_monitor_button = QPushButton("Clear")
        self.clear_monitor_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.clear_monitor_button.clicked.connect(self.clear_monitor)
        monitor_controls_layout.addWidget(self.clear_monitor_button)
        
        self.send_test_data_button = QPushButton("Send Test Data")
        self.send_test_data_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.send_test_data_button.clicked.connect(self.send_test_data)
        self.send_test_data_button.setEnabled(False)  # Disabled until monitoring starts
        monitor_controls_layout.addWidget(self.send_test_data_button)
        
        monitor_layout.addLayout(monitor_controls_layout)
        
        # Add the monitor group to the bottom splitter
        bottom_splitter.addWidget(monitor_group)
        
        # Set initial sizes for bottom splitter sections
        bottom_splitter.setSizes([self.scaler.value(400), self.scaler.value(400)])
        
        # Add the bottom splitter to the content splitter
        content_splitter.addWidget(bottom_splitter)
        
        # Set initial sizes for content splitter sections
        content_splitter.setSizes([self.scaler.value(400), self.scaler.value(300)])
        
        # Add the content splitter to the main layout
        scanner_layout.addWidget(content_splitter)
    
    def setup_fonts(self):
        """Set up fonts with proper scaling."""
        # Get consistent fonts from scaler
        table_font = self.scaler.get_code_font(self.scaler.FONT_SIZE_LARGE)
        details_font = self.scaler.get_code_font()
        
        # Apply to components
        self.ports_table.setFont(table_font)
        self.details_text.setFont(details_font)
    
    def scan_ports(self):
        """
        Scan for available serial ports and update the table.
        """
        try:
            # Get list of serial ports
            ports = serial.tools.list_ports.comports()
            
            # Store previous port names for comparison
            prev_port_names = set(self.port_info.keys())
            
            # Update port info dictionary
            current_port_names = set()
            for port in ports:
                current_port_names.add(port.device)
                
                # Store or update port info
                if port.device in self.port_info:
                    # Update existing port info
                    port_info = self.port_info[port.device]
                    port_info["device"] = port.device
                    port_info["port_name"] = port.device
                    port_info["description"] = port.description
                    port_info["manufacturer"] = port.manufacturer or "N/A"
                    port_info["hwid"] = port.hwid
                    port_info["vid"] = port.vid
                    port_info["pid"] = port.pid
                    port_info["location"] = getattr(port, "location", "N/A")
                    port_info["serial_number"] = getattr(port, "serial_number", "N/A")
                    port_info["interface"] = getattr(port, "interface", "N/A")
                else:
                    # Add new port info
                    self.port_info[port.device] = {
                        "device": port.device,  # Add device name for reference
                        "port_name": port.device,  # Alternative reference
                        "description": port.description,
                        "manufacturer": port.manufacturer or "N/A",
                        "hwid": port.hwid,
                        "vid": port.vid,
                        "pid": port.pid,
                        "status": "Unknown",
                        "location": getattr(port, "location", "N/A"),
                        "serial_number": getattr(port, "serial_number", "N/A"),
                        "interface": getattr(port, "interface", "N/A"),
                        "rx_rate": "N/A",
                        "tx_rate": "N/A"
                    }
            
            # Check for removed ports
            removed_ports = prev_port_names - current_port_names
            for port in removed_ports:
                del self.port_info[port]
            
            # Test port availability if enabled
            if self.test_ports_toggle.isChecked():
                self.test_port_availability()
            
            # Update the table
            self.update_ports_table()
            
            # Update details if a port is selected
            self.update_port_details()
            
            # Update status
            self.status_message.emit(f"Found {len(ports)} serial ports", 0)
            
        except Exception as e:
            self.error_occurred.emit(f"Error scanning ports: {str(e)}")
    
    def test_port_availability(self):
        """
        Test if ports are available by trying to open them briefly.
        Note: This might interfere with other applications using the ports.
        """
        for port_name in self.port_info:
            try:
                # Try to open the port briefly
                ser = serial.Serial(port_name, timeout=0.1)
                ser.close()
                self.port_info[port_name]["status"] = "Available"
            except serial.SerialException:
                self.port_info[port_name]["status"] = "In Use"
            except Exception:
                self.port_info[port_name]["status"] = "Error"
    
    def update_ports_table(self):
        """Update the ports table with current information."""
        # Save current selection if any
        selected_port = None
        selected_items = self.ports_table.selectedItems()
        if selected_items:
            row = self.ports_table.row(selected_items[0])
            selected_port = self.ports_table.item(row, 0).text()
        
        self.ports_table.setRowCount(0)  # Clear table
        
        for port_name, info in self.port_info.items():
            row = self.ports_table.rowCount()
            self.ports_table.insertRow(row)
            
            # Port name
            self.ports_table.setItem(row, 0, QTableWidgetItem(port_name))
            
            # Description
            self.ports_table.setItem(row, 1, QTableWidgetItem(info["description"]))
            
            # Manufacturer
            self.ports_table.setItem(row, 2, QTableWidgetItem(info["manufacturer"]))
            
            # VID:PID with enhanced extraction
            vid_pid = "N/A"
            enhanced_vid, enhanced_pid = get_enhanced_vid_pid(info)
            if enhanced_vid is not None and enhanced_pid is not None:
                vid_pid = f"{enhanced_vid:04X}:{enhanced_pid:04X}"
                # Update port info with extracted VID/PID
                info["vid"] = enhanced_vid
                info["pid"] = enhanced_pid
            self.ports_table.setItem(row, 3, QTableWidgetItem(vid_pid))
            
            # Status - use default Fusion styling
            status_item = QTableWidgetItem(info["status"])
            self.ports_table.setItem(row, 4, status_item)
            
            # Location
            self.ports_table.setItem(row, 5, QTableWidgetItem(info["location"]))
            
            # Serial Number
            self.ports_table.setItem(row, 6, QTableWidgetItem(info["serial_number"]))
        
        # Restore selection if possible
        if selected_port:
            for row in range(self.ports_table.rowCount()):
                if self.ports_table.item(row, 0).text() == selected_port:
                    self.ports_table.selectRow(row)
                    break
    
    def toggle_auto_refresh(self, enabled):
        """Toggle automatic port scanning."""
        if enabled:
            # Get refresh interval in milliseconds
            interval_text = self.refresh_interval_combo.currentText()
            seconds = int(interval_text.split()[0])
            self.scan_timer.start(seconds * 1000)
            self.status_message.emit(f"Auto-refresh enabled ({seconds}s)", 0)
        else:
            self.scan_timer.stop()
            self.status_message.emit("Auto-refresh disabled", 0)
    
    def toggle_port_testing(self, enabled):
        """Toggle testing port availability."""
        if enabled:
            self.status_message.emit("Port availability testing enabled", 0)
            # Run a test immediately
            self.test_port_availability()
            self.update_ports_table()
        else:
            self.status_message.emit("Port availability testing disabled", 0)
            # Reset status for all ports
            for port_name in self.port_info:
                self.port_info[port_name]["status"] = "Unknown"
            self.update_ports_table()
    
    def update_port_details(self):
        """Update details section when port selection changes."""
        selected_items = self.ports_table.selectedItems()
        if not selected_items:
            self.details_text.setText("Select a port to view detailed information")
            return
        
        # Get the port name from the first column
        row = self.ports_table.row(selected_items[0])
        port_name = self.ports_table.item(row, 0).text()
        
        # Get port info
        if port_name in self.port_info:
            info = self.port_info[port_name]
            
            # Format details text
            details = f"PORT: {port_name}\n\n"
            details += f"Description: {info['description']}\n"
            details += f"Manufacturer: {info['manufacturer']}\n"
            details += f"Hardware ID: {info['hwid']}\n"
            
            if info["vid"] is not None and info["pid"] is not None:
                details += f"Vendor ID: {info['vid']:04X}\n"
                details += f"Product ID: {info['pid']:04X}\n"
            
            details += f"Status: {info['status']}\n"
            details += f"Location: {info['location']}\n"
            details += f"Serial Number: {info['serial_number']}\n"
            details += f"Interface: {info['interface']}\n"
            details += f"RX Data Rate: {info['rx_rate']}\n"
            details += f"TX Data Rate: {info['tx_rate']}\n\n"
            
            # Add supported baudrates information
            details += "Standard baudrates supported by most serial devices:\n"
            details += "300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200\n\n"
            
            # Add additional info based on device type (if known)
            if "USB" in info["description"]:
                details += "USB Serial Device Information:\n"
                details += "- USB serial devices typically support all standard baudrates\n"
                details += "- Most USB-to-Serial adapters support hardware flow control\n"
                details += "- Check manufacturer website for device-specific capabilities\n"
            
            self.details_text.setText(details)
        else:
            self.details_text.setText(f"No information available for {port_name}")
    
    def test_selected_port(self):
        """Test the currently selected port for availability."""
        selected_items = self.ports_table.selectedItems()
        if not selected_items:
            self.status_message.emit("No port selected", 0)
            return
        
        # Get the port name from the first column
        row = self.ports_table.row(selected_items[0])
        port_name = self.ports_table.item(row, 0).text()
        
        # Test the port
        try:
            self.status_message.emit(f"Testing port {port_name}...", 0)
            
            # Try to open the port
            ser = serial.Serial(port_name, timeout=1)
            
            # Get additional port information
            port_info = f"PORT: {port_name}\n"
            port_info += f"Baudrate: {ser.baudrate}\n"
            port_info += f"Bytesize: {ser.bytesize}\n"
            port_info += f"Parity: {ser.parity}\n"
            port_info += f"Stopbits: {ser.stopbits}\n"
            port_info += f"Timeout: {ser.timeout}\n"
            port_info += f"XON/XOFF: {ser.xonxoff}\n"
            port_info += f"RTS/CTS: {ser.rtscts}\n"
            port_info += f"DSR/DTR: {ser.dsrdtr}\n"
            
            # Update status in port_info dictionary
            self.port_info[port_name]["status"] = "Available"
            
            # Close the port
            ser.close()
            
            # Update table
            self.update_ports_table()
            
            # Show detailed info in details text
            cursor = self.details_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText("\n\nPort test successful! Additional port information:\n")
            cursor.insertText(port_info)
            self.details_text.setTextCursor(cursor)
            
            self.status_message.emit(f"Port {port_name} is available", 0)
            
        except serial.SerialException as e:
            # Update status in port_info dictionary
            self.port_info[port_name]["status"] = "In Use"
            
            # Update table
            self.update_ports_table()
            
            # Show error in details text
            cursor = self.details_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(f"\n\nPort test failed. The port is likely in use by another application or has an error.\nError: {str(e)}")
            self.details_text.setTextCursor(cursor)
            
            self.status_message.emit(f"Port {port_name} is in use or has an error", 0)
    
    def refresh_selected_port(self):
        """Refresh information for the selected port."""
        selected_items = self.ports_table.selectedItems()
        if not selected_items:
            self.status_message.emit("No port selected", 0)
            return
        
        # Get the port name from the first column
        row = self.ports_table.row(selected_items[0])
        port_name = self.ports_table.item(row, 0).text()
        
        # Refresh port information
        try:
            # Get updated port information
            for port in serial.tools.list_ports.comports():
                if port.device == port_name:
                    # Update port info
                    self.port_info[port_name]["description"] = port.description
                    self.port_info[port_name]["manufacturer"] = port.manufacturer or "N/A"
                    self.port_info[port_name]["hwid"] = port.hwid
                    self.port_info[port_name]["vid"] = port.vid
                    self.port_info[port_name]["pid"] = port.pid
                    self.port_info[port_name]["location"] = getattr(port, "location", "N/A")
                    self.port_info[port_name]["serial_number"] = getattr(port, "serial_number", "N/A")
                    self.port_info[port_name]["interface"] = getattr(port, "interface", "N/A")
                    break
            
            # Test port availability if enabled
            if self.test_ports_toggle.isChecked():
                self.test_port_availability()
            
            # Update the table
            self.update_ports_table()
            
            # Update details
            self.update_port_details()
            
            self.status_message.emit(f"Port {port_name} information refreshed", 0)
            
        except Exception as e:
            self.error_occurred.emit(f"Error refreshing port information: {str(e)}")
    
    def identify_selected_device(self):
        """Identify the selected port device with enhanced USB descriptor and chipset analysis."""
        selected_items = self.ports_table.selectedItems()
        if not selected_items:
            self.status_message.emit("No port selected", 0)
            return
        
        # Get the port name from the first column
        row = self.ports_table.row(selected_items[0])
        port_name = self.ports_table.item(row, 0).text()
        
        if port_name not in self.port_info:
            self.status_message.emit(f"No information available for {port_name}", 0)
            return
        
        port_info = self.port_info[port_name]
        
        # Get VID/PID using enhanced extraction methods
        vid, pid = get_enhanced_vid_pid(port_info)
        
        # Use enhanced device identification
        if vid is not None and pid is not None:
            enhanced_info = get_enhanced_device_info(
                vid, 
                pid, 
                port_info.get("description")
            )
            
            # Format and display enhanced report
            cursor = self.details_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText("\n\n")
            cursor.insertText(format_enhanced_device_report(enhanced_info))
            
            # Add driver recommendations section
            basic_info = enhanced_info.get('basic_info', {})
            if basic_info.get('manufacturer'):
                cursor.insertText("\n\n===== DRIVER RECOMMENDATIONS =====\n")
                cursor.insertText(get_device_driver_recommendations(basic_info))
            
            self.details_text.setTextCursor(cursor)
            
            # Update status with confidence indication
            device_name = basic_info.get('name', 'Unknown Device')
            confidence = basic_info.get('confidence', 0)
            if confidence > 0.8:
                status_msg = f"Device identified as {device_name} (High confidence)"
            elif confidence > 0.5:
                status_msg = f"Device identified as {device_name} (Medium confidence)"
            else:
                status_msg = f"Device possibly identified as {device_name} (Low confidence)"
            
            self.status_message.emit(status_msg, 0)
        else:
            # Fallback for devices without VID/PID
            cursor = self.details_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText("\n\n===== DEVICE IDENTIFICATION =====\n")
            cursor.insertText("Could not identify device type specifically.\n")
            cursor.insertText("This appears to be a generic serial device or uses an unknown chipset.\n")
            cursor.insertText("VID/PID information not available.\n\n")
            cursor.insertText("===== DRIVER RECOMMENDATIONS =====\n")
            cursor.insertText(get_device_driver_recommendations("Unknown"))
            self.details_text.setTextCursor(cursor)
            
            self.status_message.emit("Device could not be identified - no VID/PID", 0)
    
    def autodetect_port_speed(self):
        """Attempt to automatically detect the port speed."""
        selected_items = self.ports_table.selectedItems()
        if not selected_items:
            self.status_message.emit("No port selected", 0)
            return
        
        # Get the port name from the first column
        row = self.ports_table.row(selected_items[0])
        port_name = self.ports_table.item(row, 0).text()
        
        # Create a progress dialog
        progress = QDialog(self)
        progress.setWindowTitle("Detecting Baudrate")
        progress_layout = QVBoxLayout(progress)
        
        label = QLabel("Testing common baudrates...")
        progress_layout.addWidget(label)
        
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 8)  # 8 common baudrates to test
        progress_bar.setValue(0)
        progress_layout.addWidget(progress_bar)
        
        status_label = QLabel("Testing baudrate: 115200")
        progress_layout.addWidget(status_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.rejected.connect(progress.reject)
        progress_layout.addWidget(button_box)
        
        progress.setFixedSize(QSize(300, 150))
        progress.show()
        
        # Test common baudrates
        test_speeds = [115200, 57600, 38400, 19200, 9600, 4800, 2400, 1200]
        detected_baudrate = None
        
        for i, baudrate in enumerate(test_speeds):
            if not progress.isVisible():
                break  # User cancelled
                
            # Update progress
            progress_bar.setValue(i)
            status_label.setText(f"Testing baudrate: {baudrate}")
            
            # Process events to update UI
            QApplication.processEvents()
            
            try:
                # Try to open the port at this baudrate
                ser = serial.Serial(port_name, baudrate=baudrate, timeout=0.5)
                
                # Send a test string
                ser.write(b"\r\n")
                
                # Read response and check for reasonable data
                response = ser.read(100)
                
                # Check for readable characters
                printable_chars = sum(1 for b in response if 32 <= b <= 126)
                if response and printable_chars > 2:
                    detected_baudrate = baudrate
                    ser.close()
                    break
                
                # Try a few common commands
                for cmd in [b"AT\r\n", b"help\r\n", b"?\r\n", b"version\r\n"]:
                    ser.write(cmd)
                    
                    # Process events while waiting
                    QApplication.processEvents()
                    
                    # Read response
                    response = ser.read(100)
                    
                    # Check for readable characters
                    printable_chars = sum(1 for b in response if 32 <= b <= 126)
                    if response and printable_chars > 2:
                        detected_baudrate = baudrate
                        ser.close()
                        break
                
                ser.close()
                
                if detected_baudrate:
                    break
                
            except serial.SerialException:
                # Skip this baudrate and continue
                pass
                
            # Process events to keep UI responsive
            QApplication.processEvents()
        
        # Close progress dialog
        progress.close()
        
        # Update UI with results
        if detected_baudrate:
            # Set the monitor baudrate combo to detected baudrate
            self.monitor_baudrate_combo.setCurrentText(str(detected_baudrate))
            
            # Update details
            cursor = self.details_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(f"\n\nAuto-detected baudrate: {detected_baudrate} bps\n")
            self.details_text.setTextCursor(cursor)
            
            self.status_message.emit(f"Detected baudrate: {detected_baudrate} bps", 0)
        else:
            self.status_message.emit("Could not detect baudrate automatically", 0)
            
            cursor = self.details_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText("\n\nCould not auto-detect baudrate. Try manually setting baudrate or checking device documentation.\n")
            self.details_text.setTextCursor(cursor)
    
    def toggle_port_monitoring(self, enabled):
        """Toggle monitoring of the selected port."""
        if enabled:
            # Start monitoring
            selected_items = self.ports_table.selectedItems()
            if not selected_items:
                self.status_message.emit("No port selected", 0)
                self.monitor_button.setChecked(False)
                return
            
            # Get the port name from the first column
            row = self.ports_table.row(selected_items[0])
            port_name = self.ports_table.item(row, 0).text()
            
            # Get baudrate from combo
            baudrate = int(self.monitor_baudrate_combo.currentText())
            
            # Create port monitor
            if self.port_monitor:
                self.port_monitor.stop()
                
            self.port_monitor = SerialPortMonitor(port_name, baudrate)
            self.port_monitor.stats_updated.connect(self.on_monitor_stats_updated)
            self.port_monitor.data_received.connect(self.on_monitor_data_received)
            self.port_monitor.error_occurred.connect(self.on_monitor_error)
            
            # Start monitoring
            if self.port_monitor.start():
                self.monitored_port = port_name
                self.monitor_text.clear()
                self.monitor_text.setText(f"Monitoring {port_name} at {baudrate} bps...\n\n")
                self.monitor_update_timer.start(500)  # Update display twice per second
                self.send_test_data_button.setEnabled(True)
                self.status_message.emit(f"Started monitoring {port_name}", 0)
            else:
                self.monitor_button.setChecked(False)
                self.port_monitor = None
                self.monitored_port = None
        else:
            # Stop monitoring
            if self.port_monitor:
                self.port_monitor.stop()
                self.monitor_update_timer.stop()
                self.port_monitor = None
                self.send_test_data_button.setEnabled(False)
                self.status_message.emit(f"Stopped monitoring {self.monitored_port}", 0)
                self.monitored_port = None
    
    def on_monitor_stats_updated(self, stats):
        """Handle updated statistics from port monitor."""
        # We'll update the display using the timer in update_monitor_display
        # This callback is just to receive the stats
        pass
    
    def on_monitor_data_received(self, data):
        """Handle data received from port monitor."""
        # Convert to string, handling non-printable chars
        try:
            text = data.decode('utf-8', errors='replace')
        except:
            # Show as hex if can't decode
            text = ' '.join(f'{b:02X}' for b in data)
        
        # Format for display
        formatted_text = ""
        for char in text:
            if 32 <= ord(char) <= 126 or char in '\r\n\t':
                formatted_text += char
            else:
                # Show control characters in square brackets
                formatted_text += f"[{ord(char):02X}]"
        
        # Append to monitor text
        cursor = self.monitor_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(formatted_text)
        
        # Auto-scroll
        self.monitor_text.setTextCursor(cursor)
        self.monitor_text.ensureCursorVisible()
    
    def on_monitor_error(self, error_text):
        """Handle errors from port monitor."""
        cursor = self.monitor_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(f"\n[ERROR] {error_text}\n")
        self.monitor_text.setTextCursor(cursor)
        self.error_occurred.emit(error_text)
    
    def update_monitor_display(self):
        """Update the monitoring display with latest statistics."""
        if not self.port_monitor:
            return
            
        # Get formatted stats
        stats_text = self.port_monitor.get_formatted_stats()
        
        # Update status bar
        if self.port_monitor.stats["rx_rate"] > 0 or self.port_monitor.stats["tx_rate"] > 0:
            rx_rate = self.port_monitor.stats["rx_rate"]
            tx_rate = self.port_monitor.stats["tx_rate"]
            
            if rx_rate < 1024:
                rx_rate_str = f"{rx_rate:.1f} B/s"
            else:
                rx_rate_str = f"{rx_rate/1024:.1f} KB/s"
                
            if tx_rate < 1024:
                tx_rate_str = f"{tx_rate:.1f} B/s"
            else:
                tx_rate_str = f"{tx_rate/1024:.1f} KB/s"
                
            status = f"Monitoring {self.monitored_port}: RX {rx_rate_str}, TX {tx_rate_str}"
            self.status_message.emit(status, 0)
    
    def clear_monitor(self):
        """Clear the monitor text display."""
        if self.port_monitor:
            self.monitor_text.clear()
            self.monitor_text.setText(f"Monitoring {self.monitored_port} at {self.port_monitor.baudrate} bps...\n\n")
        else:
            self.monitor_text.clear()
            self.monitor_text.setText("Select a port and click 'Monitor Port' to start monitoring")
    
    def send_test_data(self):
        """Send test data to the monitored port."""
        if not self.port_monitor:
            self.status_message.emit("Not monitoring any port", 0)
            return
            
        # Create a dialog to input test data
        dialog = QDialog(self)
        dialog.setWindowTitle("Send Test Data")
        layout = QVBoxLayout(dialog)
        
        # Add input field
        data_label = QLabel("Enter text to send:")
        layout.addWidget(data_label)
        
        data_input = QLineEdit()
        data_input.setText("AT\r\n")
        layout.addWidget(data_input)
        
        # Add options
        options_layout = QHBoxLayout()
        
        add_cr = QCheckBox("Add CR (\\r)")
        add_cr.setChecked(True)
        options_layout.addWidget(add_cr)
        
        add_lf = QCheckBox("Add LF (\\n)")
        add_lf.setChecked(True)
        options_layout.addWidget(add_lf)
        
        hex_mode = QCheckBox("Hex Mode")
        options_layout.addWidget(hex_mode)
        
        layout.addLayout(options_layout)
        
        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog and get result
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = data_input.text()
            
            # Process according to options
            if hex_mode.isChecked():
                # Convert hex string to bytes
                try:
                    # Remove any spaces or 0x prefixes
                    hex_text = text.replace(" ", "").replace("0x", "")
                    # Convert to bytes
                    data = bytes.fromhex(hex_text)
                except ValueError:
                    self.error_occurred.emit("Invalid hex format")
                    return
            else:
                # Text mode
                data = text
                
                # Add CR/LF if needed
                if add_cr.isChecked() and not text.endswith('\r'):
                    data += '\r'
                if add_lf.isChecked() and not text.endswith('\n'):
                    data += '\n'
            
            # Send the data
            if self.port_monitor.send_data(data):
                # Log in monitor text
                cursor = self.monitor_text.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.End)
                if hex_mode.isChecked():
                    hex_str = ' '.join(f'{b:02X}' for b in data)
                    cursor.insertText(f"\n[TX HEX] {hex_str}\n")
                else:
                    cursor.insertText(f"\n[TX] {text}\n")
                self.monitor_text.setTextCursor(cursor)
                
                self.status_message.emit(f"Sent {len(data)} bytes to {self.monitored_port}", 0)
            else:
                self.error_occurred.emit(f"Failed to send data to {self.monitored_port}")
    
    def export_port_info(self):
        """Export port information to CSV file."""
        if not self.port_info:
            self.status_message.emit("No port information to export", 0)
            return
            
        # Ask for file location
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Port Information", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if not file_path:
            return
            
        # Ensure file has .csv extension
        if not file_path.lower().endswith('.csv'):
            file_path += '.csv'
            
        try:
            with open(file_path, 'w', newline='') as csv_file:
                writer = csv.writer(csv_file)
                
                # Write header
                writer.writerow([
                    "Port", "Description", "Manufacturer", "VID", "PID", 
                    "Status", "Location", "Serial Number", "Hardware ID"
                ])
                
                # Write port information
                for port_name, info in self.port_info.items():
                    vid = f"{info['vid']:04X}" if info['vid'] is not None else "N/A"
                    pid = f"{info['pid']:04X}" if info['pid'] is not None else "N/A"
                    
                    writer.writerow([
                        port_name,
                        info["description"],
                        info["manufacturer"],
                        vid,
                        pid,
                        info["status"],
                        info["location"],
                        info["serial_number"],
                        info.get("hwid", "N/A")
                    ])
                    
            self.status_message.emit(f"Exported port information to {file_path}", 0)
            
        except Exception as e:
            self.error_occurred.emit(f"Error exporting port information: {str(e)}")