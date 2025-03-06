"""
Ping Scanner tab UI component.
"""
import subprocess
import csv
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget, 
                           QProgressBar, QLabel, QPushButton, QTableWidgetItem,
                           QHeaderView, QAbstractItemView, QCheckBox, QLineEdit,
                           QSpinBox, QComboBox, QMessageBox, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QTextCursor, QFont

from core.ping_scanner import PingWorker, get_ip_range, COMMON_PORTS
from utils.network_utils import get_network_adapters


class PingTab(QWidget):
    """Ping Scanner tab UI component."""
    
    # Define signals for communication with parent
    status_message = pyqtSignal(str, int)  # message, timeout
    error_occurred = pyqtSignal(str)
    
    def __init__(self, ui_scaler, parent=None):
        """
        Initialize the Ping Scanner tab component.
        
        Args:
            ui_scaler: UIScaler instance for responsive UI
            parent: Parent widget
        """
        super().__init__(parent)
        self.scaler = ui_scaler
        
        # Ping scanner variables
        self.ping_workers = []
        self.scanning = False
        self.scan_total = 0
        self.scan_complete = 0
        self.scan_results = []
        
        # Setup UI
        self.init_ui()
        self.setup_fonts()
        
        # Initialize network adapters information
        self.refresh_network_adapters()
    
    def init_ui(self):
        """Initialize the Ping Scanner tab UI."""
        ping_layout = QVBoxLayout(self)
        self.scaler.spacing(ping_layout, 10)
        self.scaler.margins(ping_layout, 10, 10, 10, 10)
        
        # Network Adapters section
        adapters_group = QGroupBox("Network Adapters")
        adapters_group.setObjectName("adaptersGroup")
        adapters_layout = QVBoxLayout(adapters_group)

        # Table for adapters
        self.adapters_table = QTableWidget(0, 5)
        self.adapters_table.setHorizontalHeaderLabels([
            "Adapter Name", "IP Address", "MAC Address", "Subnet Mask", "Default Gateway"
        ])
        self.adapters_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.adapters_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.adapters_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.adapters_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.adapters_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.adapters_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.adapters_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        adapters_layout.addWidget(self.adapters_table)

        # Refresh button for adapters
        adapters_button_layout = QHBoxLayout()
        self.refresh_adapters_button = QPushButton("Refresh Adapters")
        self.refresh_adapters_button.setObjectName("actionButton")
        self.refresh_adapters_button.clicked.connect(self.refresh_network_adapters)
        adapters_button_layout.addWidget(self.refresh_adapters_button)

        # Add a "Use Selected IP" button to fill in the start IP field with the selected adapter's IP
        self.use_selected_ip_button = QPushButton("Use Selected IP")
        self.use_selected_ip_button.setObjectName("actionButton")
        self.use_selected_ip_button.clicked.connect(self.use_selected_adapter_ip)
        adapters_button_layout.addWidget(self.use_selected_ip_button)

        adapters_button_layout.addStretch()

        adapters_layout.addLayout(adapters_button_layout)

        # Add the adapters group to the main ping layout
        ping_layout.addWidget(adapters_group)
        
        # IP Range input section
        ip_range_group = QGroupBox("IP Range")
        ip_range_group.setObjectName("connectionGroup")
        ip_range_layout = QVBoxLayout(ip_range_group)
        
        # IP Range input
        ip_input_layout = QHBoxLayout()
        
        start_ip_label = QLabel("Start IP:")
        start_ip_label.setObjectName("sectionLabel")
        self.start_ip_input = QLineEdit()
        self.start_ip_input.setPlaceholderText("192.168.1.1")
        self.start_ip_input.setObjectName("commandInput")
        
        end_ip_label = QLabel("End IP:")
        end_ip_label.setObjectName("sectionLabel")
        self.end_ip_input = QLineEdit()
        self.end_ip_input.setPlaceholderText("192.168.1.254 or leave empty for single IP")
        self.end_ip_input.setObjectName("commandInput")
        
        cidr_help_label = QLabel("(Or use CIDR notation in Start IP, e.g. 192.168.1.0/24)")
        cidr_help_label.setObjectName("helpLabel")
        
        ip_input_layout.addWidget(start_ip_label)
        ip_input_layout.addWidget(self.start_ip_input, 2)
        ip_input_layout.addWidget(end_ip_label)
        ip_input_layout.addWidget(self.end_ip_input, 2)
        
        ip_range_layout.addLayout(ip_input_layout)
        ip_range_layout.addWidget(cidr_help_label)
        
        # Scan Options
        options_layout = QHBoxLayout()
        
        # Timeout option
        timeout_label = QLabel("Timeout (ms):")
        timeout_label.setObjectName("sectionLabel")
        self.timeout_input = QSpinBox()
        self.timeout_input.setRange(100, 10000)
        self.timeout_input.setValue(1000)
        self.timeout_input.setSingleStep(100)
        self.timeout_input.setObjectName("commandInput")
        
        # DNS Resolution option
        self.dns_checkbox = QCheckBox("Perform DNS Resolution")
        self.dns_checkbox.setChecked(True)
        
        # Port Scan option
        self.port_scan_checkbox = QCheckBox("Scan Ports")
        self.port_scan_checkbox.setChecked(False)
        self.port_scan_checkbox.toggled.connect(self.toggle_port_scan_options)
        
        # Port Range combobox
        self.port_range_combo = QComboBox()
        self.port_range_combo.setEnabled(False)
        for label in COMMON_PORTS:
            self.port_range_combo.addItem(label)
        
        options_layout.addWidget(timeout_label)
        options_layout.addWidget(self.timeout_input)
        options_layout.addWidget(self.dns_checkbox)
        options_layout.addWidget(self.port_scan_checkbox)
        options_layout.addWidget(self.port_range_combo)
        options_layout.addStretch()
        
        ip_range_layout.addLayout(options_layout)
        
        # Scan button
        scan_button_layout = QHBoxLayout()
        self.scan_button = QPushButton("SCAN NETWORK")
        self.scan_button.setObjectName("connectButton")
        self.scan_button.clicked.connect(self.start_ping_scan)
        
        self.stop_scan_button = QPushButton("STOP SCAN")
        self.stop_scan_button.setObjectName("clearAllButton")
        self.stop_scan_button.clicked.connect(self.stop_ping_scan)
        self.stop_scan_button.setEnabled(False)
        
        scan_button_layout.addWidget(self.scan_button)
        scan_button_layout.addWidget(self.stop_scan_button)
        
        ip_range_layout.addLayout(scan_button_layout)
        
        ping_layout.addWidget(ip_range_group)
        
        # Progress section
        progress_group = QWidget()
        progress_layout = QHBoxLayout(progress_group)
        
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setValue(0)
        self.scan_progress.setTextVisible(True)
        self.scan_progress.setFormat("%v/%m (%p%)")
        
        self.scan_status_label = QLabel("Ready to scan")
        self.scan_status_label.setObjectName("statusLabel")
        
        progress_layout.addWidget(self.scan_progress, 3)
        progress_layout.addWidget(self.scan_status_label, 1)
        
        ping_layout.addWidget(progress_group)
        
        # Results section
        results_group = QGroupBox("Scan Results")
        results_group.setObjectName("rxPanel")
        results_layout = QVBoxLayout(results_group)
        
        # Table for results
        self.results_table = QTableWidget(0, 4)
        self.results_table.setHorizontalHeaderLabels(["IP Address", "Status", "Response Time", "Info"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        results_layout.addWidget(self.results_table)
        
        # Results control buttons
        results_buttons_layout = QHBoxLayout()
        
        self.clear_results_button = QPushButton("Clear Results")
        self.clear_results_button.setObjectName("clearButton")
        self.clear_results_button.clicked.connect(self.clear_ping_results)
        
        self.export_results_button = QPushButton("Export Results")
        self.export_results_button.setObjectName("actionButton")
        self.export_results_button.clicked.connect(self.export_ping_results)
        
        self.show_active_only_checkbox = QCheckBox("Show Active Hosts Only")
        self.show_active_only_checkbox.toggled.connect(self.filter_ping_results)
        
        results_buttons_layout.addWidget(self.clear_results_button)
        results_buttons_layout.addWidget(self.export_results_button)
        results_buttons_layout.addStretch()
        results_buttons_layout.addWidget(self.show_active_only_checkbox)
        
        results_layout.addLayout(results_buttons_layout)
        
        ping_layout.addWidget(results_group, 1)
    
    def setup_fonts(self):
        """Set up fonts with proper scaling."""
        # Define font stacks
        code_font = "JetBrains Mono, Fira Code, Source Code Pro, Consolas, Courier New"
        ui_font = "Segoe UI, Roboto, Arial, sans-serif"
        
        # Create and configure fonts with scaled size
        table_font = QFont()
        table_font.setFamily("JetBrains Mono")
        table_font.setPointSize(self.scaler.value(11))
        table_font.setStyleHint(QFont.StyleHint.Monospace)
        
        # Apply to tables
        self.adapters_table.setFont(table_font)
        self.results_table.setFont(table_font)
    
    def toggle_port_scan_options(self, enabled):
        """Enable or disable port scan options based on checkbox."""
        self.port_range_combo.setEnabled(enabled)
    
    def start_ping_scan(self):
        """Start the ping scan with current settings."""
        if self.scanning:
            return
            
        # Get IP range
        start_ip = self.start_ip_input.text().strip()
        end_ip = self.end_ip_input.text().strip()
        
        if not start_ip:
            self.error_occurred.emit("Please enter a valid IP address")
            return
            
        try:
            # Get the IP range
            ip_list = get_ip_range(start_ip, end_ip)
            
            if not ip_list:
                self.error_occurred.emit("No valid IPs in range")
                return
                
            if len(ip_list) > 1000:
                confirm = QMessageBox.question(
                    self, "Large IP Range", 
                    f"You're about to scan {len(ip_list)} IP addresses. This may take a while. Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if confirm != QMessageBox.StandardButton.Yes:
                    return
            
            # Prepare for scan
            self.scanning = True
            self.scan_total = len(ip_list)
            self.scan_complete = 0
            self.scan_results = []
            
            # Update UI
            self.scan_progress.setRange(0, self.scan_total)
            self.scan_progress.setValue(0)
            self.scan_status_label.setText(f"Scanning {self.scan_total} hosts...")
            self.scan_button.setEnabled(False)
            self.stop_scan_button.setEnabled(True)
            self.clear_results_button.setEnabled(False)
            
            # Clear previous results if any
            self.results_table.setRowCount(0)
            
            # Get scan options
            timeout_ms = self.timeout_input.value()
            dns_enabled = self.dns_checkbox.isChecked()
            
            # Port scan options
            port_scan = None
            if self.port_scan_checkbox.isChecked():
                port_range_text = self.port_range_combo.currentText()
                port_scan = COMMON_PORTS.get(port_range_text, (1, 1024))  # Default to common ports
            
            # Start workers for each IP
            self.ping_workers = []
            max_concurrent = min(100, len(ip_list))
            
            for ip in ip_list:
                worker = PingWorker(ip, timeout_ms, dns_enabled, port_scan)
                worker.result_ready.connect(self.process_ping_result)
                self.ping_workers.append(worker)
            
            # Start first batch of workers
            self.start_next_ping_workers(max_concurrent)
            
        except ValueError as e:
            self.error_occurred.emit(f"Invalid IP range: {str(e)}")
    
    def start_next_ping_workers(self, count=10):
        """
        Start next batch of ping workers.
        
        Args:
            count: Number of workers to start
        """
        if not self.scanning:
            return
            
        workers_to_start = []
        
        # Find workers that haven't been started yet
        for worker in self.ping_workers:
            if not worker.isRunning() and not worker.isFinished():
                workers_to_start.append(worker)
                if len(workers_to_start) >= count:
                    break
        
        # Start the workers
        for worker in workers_to_start:
            worker.start()
    
    @pyqtSlot(str, bool, float, str)
    def process_ping_result(self, ip, success, response_time, info):
        """
        Process ping result from worker.
        
        Args:
            ip: IP address that was pinged
            success: Whether the ping was successful
            response_time: Ping response time in ms
            info: Additional information about the host
        """
        if not self.scanning:
            return
            
        # Update progress
        self.scan_complete += 1
        self.scan_progress.setValue(self.scan_complete)
        
        # Format result
        status = "Active" if success else "Down"
        response_text = f"{response_time:.1f} ms" if success else "Timeout"
        
        # Add to results
        result = {
            "ip": ip,
            "success": success,
            "response_time": response_time,
            "info": info
        }
        self.scan_results.append(result)
        
        # Add to table if it's active or if not filtering
        if success or not self.show_active_only_checkbox.isChecked():
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            # IP Address
            ip_item = QTableWidgetItem(ip)
            self.results_table.setItem(row, 0, ip_item)
            
            # Status with color
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor("#7EC7A2" if success else "#e06c75"))
            self.results_table.setItem(row, 1, status_item)
            
            # Response time
            time_item = QTableWidgetItem(response_text)
            self.results_table.setItem(row, 2, time_item)
            
            # Info
            info_item = QTableWidgetItem(info)
            self.results_table.setItem(row, 3, info_item)
        
        # Update status
        self.scan_status_label.setText(f"Scanning: {self.scan_complete}/{self.scan_total} complete")
        
        # Check if complete
        if self.scan_complete >= self.scan_total:
            self.finish_ping_scan()
        else:
            # Start the next batch of workers
            self.start_next_ping_workers(10)
    
    def stop_ping_scan(self):
        """Stop the ongoing ping scan."""
        if not self.scanning:
            return
            
        # Stop scan
        self.scanning = False
        
        # Terminate workers
        for worker in self.ping_workers:
            if worker.isRunning():
                worker.terminate()
                worker.wait()
        
        # Update UI
        self.scan_button.setEnabled(True)
        self.stop_scan_button.setEnabled(False)
        self.clear_results_button.setEnabled(True)
        self.scan_status_label.setText(f"Scan stopped. Completed {self.scan_complete}/{self.scan_total}")
    
    def finish_ping_scan(self):
        """Complete the ping scan."""
        self.scanning = False
        
        # Update UI
        self.scan_button.setEnabled(True)
        self.stop_scan_button.setEnabled(False)
        self.clear_results_button.setEnabled(True)
        
        # Count active hosts
        active_hosts = sum(1 for result in self.scan_results if result["success"])
        
        self.scan_status_label.setText(f"Scan complete: {active_hosts} active hosts found")
    
    def clear_ping_results(self):
        """Clear the ping results table."""
        self.results_table.setRowCount(0)
        self.scan_results = []
        self.scan_progress.setValue(0)
        self.scan_status_label.setText("Ready to scan")
    
    def filter_ping_results(self, active_only):
        """
        Filter results to show only active hosts or all hosts.
        
        Args:
            active_only: Whether to show only active hosts
        """
        self.results_table.setRowCount(0)
        
        for result in self.scan_results:
            if result["success"] or not active_only:
                row = self.results_table.rowCount()
                self.results_table.insertRow(row)
                
                # IP Address
                ip_item = QTableWidgetItem(result["ip"])
                self.results_table.setItem(row, 0, ip_item)
                
                # Status with color
                status = "Active" if result["success"] else "Down"
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QColor("#7EC7A2" if result["success"] else "#e06c75"))
                self.results_table.setItem(row, 1, status_item)
                
                # Response time
                response_text = f"{result['response_time']:.1f} ms" if result["success"] else "Timeout"
                time_item = QTableWidgetItem(response_text)
                self.results_table.setItem(row, 2, time_item)
                
                # Info
                info_item = QTableWidgetItem(result["info"])
                self.results_table.setItem(row, 3, info_item)
    
    def export_ping_results(self):
        """Export ping results to a CSV file."""
        if not self.scan_results:
            self.error_occurred.emit("No results to export")
            return
            
        # Ask for filename
        filename, ok = QInputDialog.getText(self, "Export Results", "Filename (CSV):", 
                                         text="ping_scan_results.csv")
        
        if not ok or not filename:
            return
            
        if not filename.endswith('.csv'):
            filename += '.csv'
            
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(["IP Address", "Status", "Response Time (ms)", "Info"])
                
                # Write results
                for result in self.scan_results:
                    status = "Active" if result["success"] else "Down"
                    response_time = f"{result['response_time']:.1f}" if result["success"] else "Timeout"
                    
                    writer.writerow([result["ip"], status, response_time, result["info"]])
                    
            self.status_message.emit(f"Results exported to {filename}", 0)
            
        except Exception as e:
            self.error_occurred.emit(f"Error exporting results: {str(e)}")
    
    def refresh_network_adapters(self):
        """Refresh the network adapters table."""
        try:
            # Clear the table
            self.adapters_table.setRowCount(0)
            
            # Get adapter information
            adapters = get_network_adapters()
            
            if not adapters:
                self.status_message.emit("No network adapters with IP addresses found", 0)
                return
                
            # Populate the table
            for adapter in adapters:
                row = self.adapters_table.rowCount()
                self.adapters_table.insertRow(row)
                
                # Adapter Name
                name_item = QTableWidgetItem(adapter["adapter_name"])
                self.adapters_table.setItem(row, 0, name_item)
                
                # IP Addresses (first IP only in the table)
                ip_addresses = adapter.get("ip_addresses", [])
                ip_text = ip_addresses[0] if ip_addresses else "N/A"
                ip_item = QTableWidgetItem(ip_text)
                self.adapters_table.setItem(row, 1, ip_item)
                
                # MAC Address
                mac_item = QTableWidgetItem(adapter.get("mac_address", "N/A"))
                self.adapters_table.setItem(row, 2, mac_item)
                
                # Subnet Mask (first subnet only in the table)
                subnet_masks = adapter.get("subnet_masks", [])
                subnet_text = subnet_masks[0] if subnet_masks else "N/A"
                subnet_item = QTableWidgetItem(subnet_text)
                self.adapters_table.setItem(row, 3, subnet_item)
                
                # Default Gateway
                gateway_item = QTableWidgetItem(adapter.get("default_gateway", "N/A"))
                self.adapters_table.setItem(row, 4, gateway_item)
            
            self.status_message.emit(f"Found {len(adapters)} network adapters", 0)
        except Exception as e:
            self.error_occurred.emit(f"Error refreshing adapters: {str(e)}")

    def use_selected_adapter_ip(self):
        """Use the selected adapter's IP address in the Start IP field."""
        selected_rows = self.adapters_table.selectedItems()
        if not selected_rows:
            self.status_message.emit("No adapter selected", 0)
            return
            
        # Get the selected row
        row = self.adapters_table.row(selected_rows[0])
        
        # Get the IP address from the second column (index 1)
        ip_item = self.adapters_table.item(row, 1)
        if ip_item and ip_item.text() != "N/A":
            self.start_ip_input.setText(ip_item.text())
            self.status_message.emit(f"Using IP address: {ip_item.text()}", 0)
        else:
            self.status_message.emit("Selected adapter has no IP address", 0)