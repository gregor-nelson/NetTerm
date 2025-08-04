"""
Ping Scanner tab UI component - Production-ready version with comprehensive improvements.
Works with the enhanced ping_scanner core module.
"""
import os
import sys
import subprocess
import csv
import json
import threading
import weakref
from ipaddress import ip_address, AddressValueError
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget, 
                           QProgressBar, QLabel, QPushButton, QTableWidgetItem,
                           QHeaderView, QAbstractItemView, QCheckBox, QLineEdit,
                           QSpinBox, QComboBox, QMessageBox, QInputDialog,
                           QFileDialog, QMenu, QTabWidget, QTextEdit, QDialog,
                           QDialogButtonBox)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QPoint, QTimer, QMutex, QMutexLocker
from PyQt6.QtGui import QTextCursor, QFont, QAction

from core.ping_scanner import (PingWorker, get_ip_range, COMMON_PORTS, 
                              ScanProfile, export_scan_results, PRIORITY_PORTS,
                              validate_ip_address)
from utils.network_utils import get_network_adapters


class WorkerManager:
    """Manages worker threads lifecycle and cleanup"""
    def __init__(self):
        self.workers = []
        self.active_workers = set()
        self.lock = threading.Lock()
        
    def add_worker(self, worker):
        """Add a worker to be managed"""
        with self.lock:
            self.workers.append(weakref.ref(worker))
            self.active_workers.add(worker)
            
    def remove_worker(self, worker):
        """Remove a worker from active set"""
        with self.lock:
            self.active_workers.discard(worker)
            
    def stop_all(self):
        """Stop all active workers"""
        with self.lock:
            for worker in list(self.active_workers):
                if worker and hasattr(worker, 'stop'):
                    worker.stop()
                    
    def cleanup(self):
        """Clean up finished workers"""
        with self.lock:
            # Remove dead references
            self.workers = [w for w in self.workers if w() is not None]
            # Clean up finished workers
            for worker_ref in self.workers:
                worker = worker_ref()
                if worker and worker.isFinished():
                    self.active_workers.discard(worker)
                    worker.deleteLater()


class DetailedResultsDialog(QDialog):
    """Dialog for showing detailed host information"""
    def __init__(self, ip, details, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Host Details - {ip}")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Create text edit for details
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(self.parent().scaler.get_code_font() if self.parent() else QFont("Consolas", 10))
        
        # Format the details
        info_text = self.format_details(ip, details)
        self.text_edit.setPlainText(info_text)
        
        layout.addWidget(self.text_edit)
        
        # Add buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Save
        )
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.StandardButton.Save).clicked.connect(self.save_details)
        layout.addWidget(buttons)
        
    def format_details(self, ip, details):
        """Format detailed information for display"""
        info_text = f"Detailed Information for {ip}\n" + "="*60 + "\n\n"
        
        info_text += f"Status: {'Active' if details.get('alive') else 'Down'}\n"
        info_text += f"Response Time: {details.get('response_time', 0):.1f} ms\n"
        info_text += f"Hostname: {details.get('hostname', 'N/A')}\n"
        info_text += f"OS Hint: {details.get('os_hint', 'Unknown')}\n"
        info_text += f"MAC Address: {details.get('mac_address', 'N/A')}\n"
        info_text += f"Detection Method: {details.get('detection_method', 'N/A')}\n"
        info_text += f"Scan Time: {details.get('scan_time', 'N/A')}\n"
        
        if details.get('error'):
            info_text += f"Error: {details['error']}\n"
        
        info_text += "\n"
        
        # Port information
        open_ports = details.get('open_ports', [])
        if open_ports:
            info_text += f"Open Ports ({len(open_ports)}):\n"
            info_text += "-" * 40 + "\n"
            
            port_details = details.get('port_details', {})
            for port in sorted(open_ports):
                port_info = port_details.get(port, {})
                info_text += f"\nPort {port}:\n"
                info_text += f"  Service: {port_info.get('service', 'Unknown')}\n"
                if port_info.get('banner'):
                    info_text += f"  Banner: {port_info['banner'][:100]}\n"
                if port_info.get('version'):
                    info_text += f"  Version: {port_info['version']}\n"
                if port_info.get('response_time'):
                    info_text += f"  Response: {port_info['response_time']:.1f} ms\n"
                if port_info.get('method'):
                    info_text += f"  Method: {port_info['method']}\n"
        else:
            info_text += "No open ports detected\n"
            
        return info_text
    
    def save_details(self):
        """Save details to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Host Details", "host_details.txt", "Text Files (*.txt)"
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.text_edit.toPlainText())
                QMessageBox.information(self, "Success", "Details saved successfully")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")


class PingTab(QWidget):
    """Ping Scanner tab UI component - Production ready."""
    
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
        
        # Thread management
        self.worker_manager = WorkerManager()
        self.worker_cleanup_timer = QTimer()
        self.worker_cleanup_timer.timeout.connect(self.worker_manager.cleanup)
        self.worker_cleanup_timer.start(5000)  # Cleanup every 5 seconds
        
        # Thread-safe data structures
        self.data_mutex = QMutex()
        self.scan_results = []
        self.detailed_results = {}
        
        # Ping scanner variables
        self.scanning = False
        self.scan_total = 0
        self.scan_complete = 0
        
        # Progress update throttling
        self.progress_update_timer = QTimer()
        self.progress_update_timer.timeout.connect(self._update_progress_display)
        self.progress_update_timer.setInterval(100)  # Update every 100ms
        self.pending_progress = None
        
        # Setup UI
        self.init_ui()
        self.setup_fonts()
        
        # Initialize network adapters information
        self.refresh_network_adapters()
    
    def init_ui(self):
        """Initialize the Ping Scanner tab UI."""
        ping_layout = QVBoxLayout(self)
        self.scaler.spacing(ping_layout, self.scaler.SPACING_MEDIUM)
        self.scaler.margins(ping_layout, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE)
        
        # Create tabbed widget for Network Adapters and Scan Results
        self.main_tabs = QTabWidget()
        
        # Apply consistent font to main tabs
        self.main_tabs.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        
        # Create Network Adapters tab
        self.create_network_adapters_tab()
        
        # Create Scan Results tab
        self.create_scan_results_tab()
        
        # Add tabs to the tab widget
        self.main_tabs.addTab(self.adapters_tab, "Network Adapters")
        self.main_tabs.addTab(self.results_tab, "Scan Results")
        
        # Add the tabbed widget to main layout
        ping_layout.addWidget(self.main_tabs, 1)
        
        # IP Range input section
        ip_range_group = QGroupBox("IP Range")
        ip_range_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        ip_range_layout = QVBoxLayout(ip_range_group)
        self.scaler.spacing(ip_range_layout, self.scaler.SPACING_SMALL)
        
        # IP Range input
        ip_input_layout = QHBoxLayout()
        
        start_ip_label = QLabel("Start IP:")
        start_ip_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.start_ip_input = QLineEdit()
        self.start_ip_input.setFont(self.scaler.get_code_font())
        self.start_ip_input.setPlaceholderText("192.168.1.1 or 192.168.1.0/24")
        self.start_ip_input.textChanged.connect(self.validate_ip_input)
        
        end_ip_label = QLabel("End IP:")
        end_ip_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.end_ip_input = QLineEdit()
        self.end_ip_input.setFont(self.scaler.get_code_font())
        self.end_ip_input.setPlaceholderText("192.168.1.254 or leave empty for single IP")
        self.end_ip_input.textChanged.connect(self.validate_ip_input)
        
        self.ip_validation_label = QLabel("")
        self.ip_validation_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        
        ip_input_layout.addWidget(start_ip_label)
        ip_input_layout.addWidget(self.start_ip_input, 2)
        ip_input_layout.addWidget(end_ip_label)
        ip_input_layout.addWidget(self.end_ip_input, 2)
        
        ip_range_layout.addLayout(ip_input_layout)
        ip_range_layout.addWidget(self.ip_validation_label)
        
        # Scan Options
        options_layout = QHBoxLayout()
        
        # Scan Profile
        profile_label = QLabel("Scan Profile:")
        profile_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.profile_combo = QComboBox()
        self.profile_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.profile_combo.addItems(["Quick Scan", "Detailed Scan", "Custom"])
        self.profile_combo.currentTextChanged.connect(self.on_profile_changed)
        
        # Timeout option
        timeout_label = QLabel("Timeout (ms):")
        timeout_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.timeout_input = QSpinBox()
        self.timeout_input.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.timeout_input.setRange(100, 10000)
        self.timeout_input.setValue(1000)
        self.timeout_input.setSingleStep(100)
        
        # Port Scan option
        self.port_scan_checkbox = QCheckBox("Scan Ports")
        self.port_scan_checkbox.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.port_scan_checkbox.setChecked(False)
        self.port_scan_checkbox.toggled.connect(self.toggle_port_scan_options)
        
        # Port Range combobox
        self.port_range_combo = QComboBox()
        self.port_range_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.port_range_combo.setEnabled(False)
        for label in COMMON_PORTS:
            self.port_range_combo.addItem(label)
        
        options_layout.addWidget(profile_label)
        options_layout.addWidget(self.profile_combo)
        options_layout.addWidget(timeout_label)
        options_layout.addWidget(self.timeout_input)
        options_layout.addWidget(self.port_scan_checkbox)
        options_layout.addWidget(self.port_range_combo, 2)
        options_layout.addStretch()
        
        ip_range_layout.addLayout(options_layout)
        
        # Scan button
        scan_button_layout = QHBoxLayout()
        self.scaler.spacing(scan_button_layout, self.scaler.SPACING_SMALL)
        
        self.scan_button = QPushButton("Scan Network")
        self.scan_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        self.scan_button.clicked.connect(self.start_ping_scan)
        
        # Remove custom styling - use theme system
        
        self.stop_scan_button = QPushButton("Stop Scan")
        self.stop_scan_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.stop_scan_button.clicked.connect(self.stop_ping_scan)
        self.stop_scan_button.setEnabled(False)
        
        # Remove custom styling - use theme system
        
        # Estimate time button
        self.estimate_button = QPushButton("Estimate Time")
        self.estimate_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.estimate_button.clicked.connect(self.estimate_scan_time)
        
        scan_button_layout.addWidget(self.scan_button)
        scan_button_layout.addWidget(self.stop_scan_button)
        scan_button_layout.addWidget(self.estimate_button)
        
        ip_range_layout.addLayout(scan_button_layout)
        
        ping_layout.addWidget(ip_range_group)
        
        # Progress section
        progress_group = QWidget()
        progress_layout = QVBoxLayout(progress_group)
        
        # Main progress
        self.scan_progress = QProgressBar()
        self.scan_progress.setRange(0, 100)
        self.scan_progress.setValue(0)
        self.scan_progress.setTextVisible(True)
        self.scan_progress.setFormat("%v/%m (%p%)")
        
        # Port scan progress
        self.port_scan_progress = QProgressBar()
        self.port_scan_progress.setRange(0, 100)
        self.port_scan_progress.setValue(0)
        self.port_scan_progress.setTextVisible(True)
        self.port_scan_progress.setFormat("Port scan: %v/%m")
        self.port_scan_progress.setVisible(False)
        
        self.scan_status_label = QLabel("Ready to scan")
        self.scan_status_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        
        # Time estimate label
        self.time_estimate_label = QLabel("")
        self.time_estimate_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        
        progress_layout.addWidget(self.scan_progress)
        progress_layout.addWidget(self.port_scan_progress)
        progress_layout.addWidget(self.scan_status_label)
        progress_layout.addWidget(self.time_estimate_label)
        
        ping_layout.addWidget(progress_group)
    
    def create_network_adapters_tab(self):
        """Create the Network Adapters tab."""
        self.adapters_tab = QWidget()
        adapters_layout = QVBoxLayout(self.adapters_tab)
        self.scaler.spacing(adapters_layout, self.scaler.SPACING_MEDIUM)
        self.scaler.margins(adapters_layout, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE)

        # Network Adapters content
        adapters_group = QGroupBox("Network Adapters")
        adapters_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        adapters_group_layout = QVBoxLayout(adapters_group)
        self.scaler.spacing(adapters_group_layout, self.scaler.SPACING_SMALL)

        # Table for adapters
        self.adapters_table = QTableWidget(0, 6)
        self.adapters_table.setHorizontalHeaderLabels([
            "Adapter Name", "IP Address", "MAC Address", 
            "Subnet Mask", "Default Gateway", "Status"
        ])
        self.adapters_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            self.adapters_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self.adapters_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.adapters_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.adapters_table.setAlternatingRowColors(True)

        adapters_group_layout.addWidget(self.adapters_table)

        # Refresh button for adapters
        adapters_button_layout = QHBoxLayout()
        self.scaler.spacing(adapters_button_layout, self.scaler.SPACING_SMALL)
        
        self.refresh_adapters_button = QPushButton("Refresh Adapters")
        self.refresh_adapters_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.refresh_adapters_button.clicked.connect(self.refresh_network_adapters)
        adapters_button_layout.addWidget(self.refresh_adapters_button)

        # Add a "Use Selected IP" button to fill in the start IP field
        self.use_selected_ip_button = QPushButton("Use Selected IP")
        self.use_selected_ip_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.use_selected_ip_button.clicked.connect(self.use_selected_adapter_ip)
        adapters_button_layout.addWidget(self.use_selected_ip_button)
        
        # Scan local network button
        self.scan_local_button = QPushButton("Scan Local Network")
        self.scan_local_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        self.scan_local_button.clicked.connect(self.scan_local_network)
        adapters_button_layout.addWidget(self.scan_local_button)

        adapters_button_layout.addStretch()

        adapters_group_layout.addLayout(adapters_button_layout)
        
        # Add the adapters group to the tab layout
        adapters_layout.addWidget(adapters_group)
        adapters_layout.addStretch()  # Add stretch to push content to top
    
    def create_scan_results_tab(self):
        """Create the Scan Results tab."""
        self.results_tab = QWidget()
        results_layout = QVBoxLayout(self.results_tab)
        self.scaler.spacing(results_layout, self.scaler.SPACING_MEDIUM)
        self.scaler.margins(results_layout, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE)
        
        # Results section
        results_group = QGroupBox("Scan Results")
        results_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        results_group_layout = QVBoxLayout(results_group)
        self.scaler.spacing(results_group_layout, self.scaler.SPACING_SMALL)
        
        # Summary label
        self.results_summary_label = QLabel("No scan results yet")
        self.results_summary_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        results_group_layout.addWidget(self.results_summary_label)
        
        # Table for results
        self.results_table = QTableWidget(0, 7)
        self.results_table.setHorizontalHeaderLabels([
            "IP Address", "Status", "Response Time", "Hostname", "OS", "Ports/Services", "MAC"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSortingEnabled(True)
        
        # Add context menu for detailed view
        self.results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Double-click to view details
        self.results_table.itemDoubleClicked.connect(self.on_result_double_clicked)
        
        results_group_layout.addWidget(self.results_table)
        
        # Results control buttons
        results_buttons_layout = QHBoxLayout()
        self.scaler.spacing(results_buttons_layout, self.scaler.SPACING_SMALL)
        
        self.clear_results_button = QPushButton("Clear Results")
        self.clear_results_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.clear_results_button.clicked.connect(self.clear_ping_results)
        
        self.export_results_button = QPushButton("Export Results")
        self.export_results_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.export_results_button.clicked.connect(self.export_ping_results)
        
        self.show_active_only_checkbox = QCheckBox("Show Active Hosts Only")
        self.show_active_only_checkbox.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.show_active_only_checkbox.toggled.connect(self.filter_ping_results)
        
        results_buttons_layout.addWidget(self.clear_results_button)
        results_buttons_layout.addWidget(self.export_results_button)
        results_buttons_layout.addStretch()
        results_buttons_layout.addWidget(self.show_active_only_checkbox)
        
        results_group_layout.addLayout(results_buttons_layout)
        
        # Add the results group to the tab layout
        results_layout.addWidget(results_group)
    
    def setup_fonts(self):
        """Set up fonts with proper scaling."""
        # Get consistent fonts from scaler
        table_font = self.scaler.get_code_font(self.scaler.FONT_SIZE_LARGE)
        
        # Apply to tables
        self.adapters_table.setFont(table_font)
        self.results_table.setFont(table_font)
    
    def validate_ip_input(self):
        """Validate IP address inputs in real-time"""
        start_ip = self.start_ip_input.text().strip()
        end_ip = self.end_ip_input.text().strip()
        
        validation_errors = []
        
        # Validate start IP
        if start_ip:
            if '/' in start_ip:
                # CIDR notation
                try:
                    import ipaddress
                    network = ipaddress.ip_network(start_ip, strict=False)
                    if network.num_addresses > 1024:
                        validation_errors.append("Network too large (max 1024 IPs)")
                except ValueError:
                    validation_errors.append("Invalid CIDR notation")
            else:
                # Regular IP
                if not validate_ip_address(start_ip):
                    validation_errors.append("Invalid start IP address")
        
        # Validate end IP if provided
        if end_ip and not validate_ip_address(end_ip):
            validation_errors.append("Invalid end IP address")
        
        # Check range validity
        if start_ip and end_ip and not validation_errors:
            try:
                start = ip_address(start_ip)
                end = ip_address(end_ip)
                if start > end:
                    validation_errors.append("Start IP must be <= End IP")
            except:
                pass
        
        # Update validation label
        if validation_errors:
            self.ip_validation_label.setText("; ".join(validation_errors))
            self.scan_button.setEnabled(False)
        else:
            self.ip_validation_label.setText("")
            self.scan_button.setEnabled(not self.scanning)
    
    def on_profile_changed(self, profile_name):
        """Handle scan profile change."""
        if profile_name == "Quick Scan":
            self.timeout_input.setValue(500)
            self.port_scan_checkbox.setChecked(False)
        elif profile_name == "Detailed Scan":
            self.timeout_input.setValue(2000)
            self.port_scan_checkbox.setChecked(True)
            self.port_range_combo.setCurrentText("Standard Scan (1-1024)")
        # Custom profile allows manual configuration
    
    def toggle_port_scan_options(self, enabled):
        """Enable or disable port scan options based on checkbox."""
        self.port_range_combo.setEnabled(enabled)
        self.port_scan_progress.setVisible(enabled and self.scanning)
        
        # Update time estimate
        self.estimate_scan_time()
    
    def estimate_scan_time(self):
        """Estimate scan time based on current settings"""
        try:
            # Get IP range
            start_ip = self.start_ip_input.text().strip()
            end_ip = self.end_ip_input.text().strip()
            
            if not start_ip:
                self.time_estimate_label.setText("")
                return
            
            ip_list = get_ip_range(start_ip, end_ip)
            num_ips = len(ip_list)
            
            # Base time per IP
            timeout_ms = self.timeout_input.value()
            base_time_per_ip = timeout_ms / 1000.0
            
            # Port scan time
            port_time = 0
            if self.port_scan_checkbox.isChecked():
                port_range_text = self.port_range_combo.currentText()
                port_range_value = COMMON_PORTS.get(port_range_text)
                
                if port_range_value == "priority":
                    num_ports = len(PRIORITY_PORTS)
                elif isinstance(port_range_value, tuple):
                    num_ports = min(port_range_value[1] - port_range_value[0] + 1, 200)
                else:
                    num_ports = 50
                
                # Estimate based on parallel scanning
                port_time = (num_ports * 0.05)  # 50ms per port average
            
            # Total time estimate
            total_time = num_ips * (base_time_per_ip + port_time)
            
            # Format time
            if total_time < 60:
                time_str = f"{total_time:.0f} seconds"
            else:
                minutes = int(total_time // 60)
                seconds = int(total_time % 60)
                time_str = f"{minutes}m {seconds}s"
            
            self.time_estimate_label.setText(f"Estimated time: ~{time_str} for {num_ips} IPs")
            
        except Exception:
            self.time_estimate_label.setText("")
    
    def scan_local_network(self):
        """Scan the local network of the selected adapter"""
        selected_rows = self.adapters_table.selectedItems()
        if not selected_rows:
            self.status_message.emit("Please select a network adapter first", 3000)
            return
        
        # Get the selected row
        row = self.adapters_table.row(selected_rows[0])
        
        # Get IP and subnet from the table
        ip_item = self.adapters_table.item(row, 1)
        subnet_item = self.adapters_table.item(row, 3)
        
        if not ip_item or not subnet_item or ip_item.text() == "N/A":
            self.status_message.emit("Selected adapter has no valid IP configuration", 3000)
            return
        
        try:
            # Calculate network CIDR
            import ipaddress
            ip = ip_item.text()
            subnet = subnet_item.text()
            
            # Create network from IP and subnet mask
            interface = ipaddress.IPv4Interface(f"{ip}/{subnet}")
            network = interface.network
            
            # Set the IP range
            self.start_ip_input.setText(str(network))
            self.end_ip_input.setText("")
            
            # Switch to results tab
            self.main_tabs.setCurrentIndex(1)
            
            # Start scan
            self.start_ping_scan()
            
        except Exception as e:
            self.error_occurred.emit(f"Failed to calculate network: {str(e)}")
    
    def start_ping_scan(self):
        """Start the ping scan with current settings."""
        if self.scanning:
            return
        
        # Validate IPs first
        self.validate_ip_input()
        if self.ip_validation_label.text():
            return
            
        # Automatically switch to results tab when scan starts
        self.main_tabs.setCurrentIndex(1)
            
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
                
            if len(ip_list) > 256:
                confirm = QMessageBox.question(
                    self, "Large IP Range", 
                    f"You're about to scan {len(ip_list)} IP addresses. This may take a while.\n\n"
                    f"Estimated time: {self.time_estimate_label.text()}\n\nContinue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if confirm != QMessageBox.StandardButton.Yes:
                    return
            
            # Prepare for scan
            self.scanning = True
            self.scan_total = len(ip_list)
            self.scan_complete = 0
            
            # Clear previous data - thread safe
            with QMutexLocker(self.data_mutex):
                self.scan_results.clear()
                self.detailed_results.clear()
            
            # Update UI
            self.scan_progress.setRange(0, self.scan_total)
            self.scan_progress.setValue(0)
            self.scan_status_label.setText(f"Scanning {self.scan_total} hosts...")
            self.scan_button.setEnabled(False)
            self.stop_scan_button.setEnabled(True)
            self.clear_results_button.setEnabled(False)
            self.results_summary_label.setText(f"Scanning {self.scan_total} hosts...")
            
            # Clear previous results
            self.results_table.setRowCount(0)
            self.results_table.setSortingEnabled(False)  # Disable sorting during scan
            
            # Start progress timer
            self.progress_update_timer.start()
            
            # Get scan options
            timeout_ms = self.timeout_input.value()
            
            # Build profile based on selections
            profile_name = self.profile_combo.currentText()
            if profile_name == "Quick Scan":
                profile = ScanProfile.QUICK.copy()
            elif profile_name == "Detailed Scan":
                profile = ScanProfile.DETAILED.copy()
            else:
                profile = ScanProfile.CUSTOM.copy()
            
            # Override with user settings
            profile['timeout_ms'] = timeout_ms
            
            # Port scan options
            port_range = None
            if self.port_scan_checkbox.isChecked():
                port_range_text = self.port_range_combo.currentText()
                port_range_value = COMMON_PORTS.get(port_range_text)
                
                if port_range_value == "priority":
                    profile['ports'] = PRIORITY_PORTS
                    port_range = (1, 65535)  # Will be filtered by profile
                elif isinstance(port_range_value, tuple):
                    port_range = port_range_value
                    if 'ports' in profile:
                        del profile['ports']
                else:
                    port_range = (1, 1024)  # Default
                    if 'ports' in profile:
                        del profile['ports']
            
            # Create and start workers
            max_concurrent = min(50, len(ip_list))
            
            for ip in ip_list:
                worker = PingWorker(ip, timeout_ms, profile, port_range)
                worker.result_ready.connect(self.process_ping_result)
                worker.progress_update.connect(self.on_progress_update)
                worker.detailed_info.connect(self.on_detailed_info)
                worker.port_scan_progress.connect(self.on_port_scan_progress)
                worker.error_occurred.connect(self.on_worker_error)
                
                # Add to manager
                self.worker_manager.add_worker(worker)
            
            # Start first batch of workers
            self.start_next_ping_workers(max_concurrent)
            
        except ValueError as e:
            self.scanning = False
            self.error_occurred.emit(f"Invalid IP range: {str(e)}")
    
    def start_next_ping_workers(self, count=10):
        """Start next batch of ping workers - thread safe."""
        if not self.scanning:
            return
        
        started = 0
        with self.worker_manager.lock:
            for worker_ref in self.worker_manager.workers:
                worker = worker_ref()
                if worker and not worker.isRunning() and not worker.isFinished():
                    try:
                        worker.start()
                        started += 1
                        if started >= count:
                            break
                    except RuntimeError:
                        # Worker might have been started elsewhere
                        pass
    
    @pyqtSlot(str, int, int)
    def on_progress_update(self, status, current, total):
        """Handle progress updates from workers."""
        if self.scanning:
            self.scan_status_label.setText(f"{status} ({self.scan_complete}/{self.scan_total} hosts)")
    
    @pyqtSlot(str, dict)
    def on_detailed_info(self, ip, info):
        """Store detailed information for each IP - thread safe."""
        with QMutexLocker(self.data_mutex):
            self.detailed_results[ip] = info
    
    @pyqtSlot(int, int)
    def on_port_scan_progress(self, scanned, total):
        """Update port scan progress with throttling."""
        if self.port_scan_checkbox.isChecked():
            self.pending_progress = (scanned, total)
    
    def _update_progress_display(self):
        """Update progress display from timer to prevent UI flooding"""
        if self.pending_progress:
            scanned, total = self.pending_progress
            self.port_scan_progress.setRange(0, total)
            self.port_scan_progress.setValue(scanned)
            self.pending_progress = None
    
    @pyqtSlot(str, str)
    def on_worker_error(self, ip, error_msg):
        """Handle worker errors"""
        self.status_message.emit(f"Error scanning {ip}: {error_msg}", 5000)
    
    @pyqtSlot(str, bool, float, str)
    def process_ping_result(self, ip, success, response_time, summary):
        """Process ping result from worker - thread safe."""
        if not self.scanning:
            return
            
        # Update progress
        self.scan_complete += 1
        self.scan_progress.setValue(self.scan_complete)
        
        # Get detailed info if available - thread safe
        with QMutexLocker(self.data_mutex):
            detailed_info = self.detailed_results.get(ip, {})
        
        # Format result for storage
        result = {
            "ip": ip,
            "success": success,
            "response_time": response_time,
            "summary": summary,
            "detailed": detailed_info
        }
        
        # Store result - thread safe
        with QMutexLocker(self.data_mutex):
            self.scan_results.append(result)
        
        # Add to table if it's active or if not filtering
        if success or not self.show_active_only_checkbox.isChecked():
            self.add_result_to_table(result)
        
        # Update status
        active_count = sum(1 for r in self.scan_results if r["success"])
        self.scan_status_label.setText(
            f"Scanning: {self.scan_complete}/{self.scan_total} complete "
            f"({active_count} active)"
        )
        
        # Check if complete
        if self.scan_complete >= self.scan_total:
            self.finish_ping_scan()
        else:
            # Start the next batch of workers
            self.start_next_ping_workers(10)
    
    def add_result_to_table(self, result):
        """Add a result to the table."""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        # IP Address
        ip_item = QTableWidgetItem(result["ip"])
        self.results_table.setItem(row, 0, ip_item)
        
        # Status with color - using QPalette-based colors
        status = "Active" if result["success"] else "Down"
        status_item = QTableWidgetItem(status)
        # Use default Fusion styling
        self.results_table.setItem(row, 1, status_item)
        
        # Response time
        response_text = f"{result['response_time']:.1f} ms" if result["success"] else "Timeout"
        time_item = QTableWidgetItem(response_text)
        # Make response time sortable numerically
        time_item.setData(Qt.ItemDataRole.UserRole, result['response_time'])
        self.results_table.setItem(row, 2, time_item)
        
        # Extract info from detailed results
        detailed = result.get("detailed", {})
        
        # Hostname
        hostname = detailed.get("hostname", "N/A")
        hostname_item = QTableWidgetItem(hostname)
        self.results_table.setItem(row, 3, hostname_item)
        
        # OS
        os_hint = detailed.get("os_hint", "Unknown")
        os_item = QTableWidgetItem(os_hint)
        self.results_table.setItem(row, 4, os_item)
        
        # Ports/Services - create a summary
        ports_summary = self.create_ports_summary(detailed)
        ports_item = QTableWidgetItem(ports_summary)
        self.results_table.setItem(row, 5, ports_item)
        
        # MAC Address
        mac = detailed.get("mac_address", "N/A")
        mac_item = QTableWidgetItem(mac if mac else "N/A")
        self.results_table.setItem(row, 6, mac_item)
    
    def create_ports_summary(self, detailed_info):
        """Create a summary of ports and services."""
        open_ports = detailed_info.get("open_ports", [])
        port_details = detailed_info.get("port_details", {})
        
        if not open_ports:
            return "No open ports"
        
        # Create summary of first few ports with services
        summary_parts = []
        for port in open_ports[:5]:
            details = port_details.get(port, {})
            service = details.get("service", "Unknown")
            summary_parts.append(f"{port}/{service}")
        
        summary = ", ".join(summary_parts)
        if len(open_ports) > 5:
            summary += f" +{len(open_ports)-5} more"
        
        return summary
    
    def show_context_menu(self, position: QPoint):
        """Show context menu for results table."""
        item = self.results_table.itemAt(position)
        if item is None:
            return
        
        row = self.results_table.row(item)
        ip = self.results_table.item(row, 0).text()
        
        menu = QMenu(self)
        
        # View Details action
        view_details_action = QAction("View Details", self)
        view_details_action.triggered.connect(lambda: self.show_host_details(ip))
        menu.addAction(view_details_action)
        
        # Copy IP action
        copy_ip_action = QAction("Copy IP Address", self)
        copy_ip_action.triggered.connect(lambda: self.copy_to_clipboard(ip))
        menu.addAction(copy_ip_action)
        
        # Copy entire row
        copy_row_action = QAction("Copy Row", self)
        copy_row_action.triggered.connect(lambda: self.copy_row_to_clipboard(row))
        menu.addAction(copy_row_action)
        
        menu.addSeparator()
        
        # Export single host
        export_host_action = QAction("Export Host Details", self)
        export_host_action.triggered.connect(lambda: self.export_single_host(ip))
        menu.addAction(export_host_action)
        
        # Show menu
        menu.exec(self.results_table.mapToGlobal(position))
    
    def on_result_double_clicked(self, item):
        """Handle double-click on result"""
        row = self.results_table.row(item)
        ip = self.results_table.item(row, 0).text()
        self.show_host_details(ip)
    
    def show_host_details(self, ip):
        """Show detailed information for a host in a dialog."""
        with QMutexLocker(self.data_mutex):
            details = self.detailed_results.get(ip)
        
        if not details:
            self.status_message.emit("No detailed information available", 3000)
            return
        
        # Show detailed dialog
        dialog = DetailedResultsDialog(ip, details, self)
        dialog.exec()
    
    def copy_to_clipboard(self, text):
        """Copy text to clipboard."""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
        self.status_message.emit(f"Copied to clipboard: {text}", 2000)
    
    def copy_row_to_clipboard(self, row):
        """Copy entire row to clipboard"""
        from PyQt6.QtWidgets import QApplication
        
        row_data = []
        for col in range(self.results_table.columnCount()):
            item = self.results_table.item(row, col)
            row_data.append(item.text() if item else "")
        
        QApplication.clipboard().setText("\t".join(row_data))
        self.status_message.emit("Row copied to clipboard", 2000)
    
    def export_single_host(self, ip):
        """Export single host details"""
        with QMutexLocker(self.data_mutex):
            details = self.detailed_results.get(ip)
        
        if not details:
            self.status_message.emit("No details to export", 3000)
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, f"Save {ip} Details", f"host_{ip.replace('.', '_')}.json", 
            "JSON Files (*.json)"
        )
        
        if filename:
            try:
                import json
                with open(filename, 'w') as f:
                    json.dump(details, f, indent=2, default=str)
                self.status_message.emit(f"Exported to {filename}", 0)
            except Exception as e:
                self.error_occurred.emit(f"Export failed: {str(e)}")
    
    def stop_ping_scan(self):
        """Stop the ongoing ping scan."""
        if not self.scanning:
            return
            
        # Stop scan
        self.scanning = False
        
        # Stop all workers
        self.worker_manager.stop_all()
        
        # Stop timers
        self.progress_update_timer.stop()
        
        # Update UI
        self.scan_button.setEnabled(True)
        self.stop_scan_button.setEnabled(False)
        self.clear_results_button.setEnabled(True)
        self.scan_status_label.setText(f"Scan stopped. Completed {self.scan_complete}/{self.scan_total}")
        self.port_scan_progress.setVisible(False)
        self.results_table.setSortingEnabled(True)
        
        # Update summary
        self.update_results_summary()
    
    def finish_ping_scan(self):
        """Complete the ping scan."""
        self.scanning = False
        
        # Stop timers
        self.progress_update_timer.stop()
        
        # Clean up workers
        self.worker_manager.cleanup()
        
        # Update UI
        self.scan_button.setEnabled(True)
        self.stop_scan_button.setEnabled(False)
        self.clear_results_button.setEnabled(True)
        self.port_scan_progress.setVisible(False)
        self.results_table.setSortingEnabled(True)
        
        # Update summary
        self.update_results_summary()
        
        # Status message
        active_hosts = sum(1 for result in self.scan_results if result["success"])
        self.scan_status_label.setText(f"Scan complete: {active_hosts} active hosts found")
        self.status_message.emit(f"Scan complete: {active_hosts} active hosts found", 0)
    
    def update_results_summary(self):
        """Update results summary label"""
        with QMutexLocker(self.data_mutex):
            total = len(self.scan_results)
            active = sum(1 for r in self.scan_results if r["success"])
            
        if total == 0:
            self.results_summary_label.setText("No scan results yet")
        else:
            self.results_summary_label.setText(
                f"Total: {total} hosts | Active: {active} | Down: {total - active}"
            )
    
    def clear_ping_results(self):
        """Clear the ping results table and data."""
        self.results_table.setRowCount(0)
        
        # Thread-safe clear
        with QMutexLocker(self.data_mutex):
            self.scan_results.clear()
            self.detailed_results.clear()
        
        self.scan_progress.setValue(0)
        self.port_scan_progress.setValue(0)
        self.scan_status_label.setText("Ready to scan")
        self.results_summary_label.setText("No scan results yet")
    
    def filter_ping_results(self, active_only):
        """Filter results to show only active hosts or all hosts."""
        self.results_table.setRowCount(0)
        self.results_table.setSortingEnabled(False)
        
        # Thread-safe iteration
        with QMutexLocker(self.data_mutex):
            results_copy = self.scan_results.copy()
        
        for result in results_copy:
            if result["success"] or not active_only:
                self.add_result_to_table(result)
        
        self.results_table.setSortingEnabled(True)
    
    def export_ping_results(self):
        """Export ping results to various formats."""
        with QMutexLocker(self.data_mutex):
            if not self.scan_results:
                self.error_occurred.emit("No results to export")
                return
        
        # Ask for format
        formats = ["JSON (Full Details)", "CSV (Summary)", "Text Report", "XML"]
        format_choice, ok = QInputDialog.getItem(
            self, "Export Format", "Select export format:", formats, 0, False
        )
        
        if not ok:
            return
        
        # Map choice to format
        format_map = {
            "JSON (Full Details)": ("json", "JSON Files (*.json)"),
            "CSV (Summary)": ("csv", "CSV Files (*.csv)"),
            "Text Report": ("text", "Text Files (*.txt)"),
            "XML": ("xml", "XML Files (*.xml)")
        }
        
        format_type, file_filter = format_map.get(format_choice, ("json", "JSON Files (*.json)"))
        
        # Ask for filename
        default_name = f"scan_results_{self.scan_complete}_hosts"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Results", f"{default_name}.{format_type}", file_filter
        )
        
        if not filename:
            return
        
        try:
            # Prepare data for export
            with QMutexLocker(self.data_mutex):
                if format_type == "xml":
                    # Custom XML export
                    self.export_to_xml(filename, self.detailed_results.values())
                else:
                    # Use the export function for other formats
                    export_data = []
                    for result in self.scan_results:
                        if result["success"] or format_type == "json":
                            export_data.append(result.get("detailed", {}))
                    
                    exported_content = export_scan_results(export_data, format_type)
                    
                    # Write to file
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(exported_content)
            
            self.status_message.emit(f"Results exported to {filename}", 0)
            
        except Exception as e:
            self.error_occurred.emit(f"Error exporting results: {str(e)}")
    
    def export_to_xml(self, filename, results):
        """Export results to XML format"""
        import xml.etree.ElementTree as ET
        
        root = ET.Element("scan_results")
        root.set("total", str(len(results)))
        
        for result in results:
            host = ET.SubElement(root, "host")
            host.set("ip", result.get("ip", ""))
            host.set("alive", str(result.get("alive", False)))
            
            # Add child elements
            ET.SubElement(host, "hostname").text = result.get("hostname", "N/A")
            ET.SubElement(host, "response_time").text = str(result.get("response_time", 0))
            ET.SubElement(host, "os_hint").text = result.get("os_hint", "Unknown")
            ET.SubElement(host, "mac_address").text = result.get("mac_address", "N/A")
            
            # Add ports
            ports = ET.SubElement(host, "ports")
            for port in result.get("open_ports", []):
                port_elem = ET.SubElement(ports, "port")
                port_elem.set("number", str(port))
                port_details = result.get("port_details", {}).get(port, {})
                port_elem.set("service", port_details.get("service", "Unknown"))
        
        # Write to file
        tree = ET.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
    
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
                
                # Status (simplified) - using QPalette-based colors
                status = "Active" if ip_addresses else "Inactive"
                status_item = QTableWidgetItem(status)
                # Use default Fusion styling
                self.adapters_table.setItem(row, 5, status_item)
            
            self.status_message.emit(f"Found {len(adapters)} network adapters", 3000)
        except Exception as e:
            self.error_occurred.emit(f"Error refreshing adapters: {str(e)}")

    def use_selected_adapter_ip(self):
        """Use the selected adapter's IP address in the Start IP field."""
        selected_rows = self.adapters_table.selectedItems()
        if not selected_rows:
            self.status_message.emit("No adapter selected", 3000)
            return
            
        # Get the selected row
        row = self.adapters_table.row(selected_rows[0])
        
        # Get the IP address from the second column (index 1)
        ip_item = self.adapters_table.item(row, 1)
        if ip_item and ip_item.text() != "N/A":
            self.start_ip_input.setText(ip_item.text())
            self.status_message.emit(f"Using IP address: {ip_item.text()}", 3000)
        else:
            self.status_message.emit("Selected adapter has no IP address", 3000)
    
    def closeEvent(self, event):
        """Clean up resources when widget is closed."""
        # Stop any ongoing scan
        if self.scanning:
            self.stop_ping_scan()
        
        # Stop timers
        self.worker_cleanup_timer.stop()
        self.progress_update_timer.stop()
        
        # Clean up workers
        self.worker_manager.stop_all()
        self.worker_manager.cleanup()
        
        event.accept()