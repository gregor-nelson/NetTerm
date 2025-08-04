"""
Enhanced Serial Monitor tab UI component with improved layout and features.
"""
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                           QLineEdit, QPushButton, QLabel, QComboBox, 
                           QInputDialog, QMessageBox, QGroupBox, QSplitter,
                           QFrame, QFileDialog, QCompleter)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QFont

from core.serial_monitor import SerialMonitor
from core.serial_thread import SerialThread
from core.command_sequence import CommandSequence


class SerialTab(QWidget):
    """Enhanced Serial Monitor tab UI component."""
    
    # Define signals for communication with parent
    status_message = pyqtSignal(str, int)  # message, timeout
    error_occurred = pyqtSignal(str)
    
    def __init__(self, ui_scaler, parent=None):
        """
        Initialize the Enhanced Serial tab component.
        
        Args:
            ui_scaler: UIScaler instance for responsive UI
            parent: Parent widget
        """
        super().__init__(parent)
        self.scaler = ui_scaler
        
        # Initialize components
        self.monitor = None
        self.serial_thread = None
        self.current_sequence = None
        self.auto_clear_rx = True  # Flag for auto-clearing RX on command
        
        # Initialize command sequences
        self.command_sequences = {}
        self.sequences_dir = os.path.join(os.path.expanduser("~"), ".serial_monitor", "sequences")
        os.makedirs(self.sequences_dir, exist_ok=True)
        self.load_sequences()
        
        # Setup UI
        self.init_ui()
        self.setup_fonts()
        self.setup_command_completer()
        self.update_port_list()
        
        # Initialize stats
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.last_rx = 0
        self.last_tx = 0
        self.last_time = datetime.now()
        
        # Create timer for stats update
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)  # Update every second
    
    def init_ui(self):
        """Initialize the Enhanced Serial Monitor tab UI."""
        main_layout = QVBoxLayout(self)
        self.scaler.spacing(main_layout, self.scaler.SPACING_MEDIUM)
        self.scaler.margins(main_layout, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE, self.scaler.SPACING_LARGE)
        
        
        # Create the main splitter for flexible layout
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)
        
        # Top control panel with connection and sequence controls
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        self.scaler.spacing(top_layout, self.scaler.SPACING_MEDIUM)
        
        # Connection controls group
        connection_group = QGroupBox("Connection Settings")
        connection_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        connection_layout = QVBoxLayout(connection_group)
        self.scaler.spacing(connection_layout, self.scaler.SPACING_SMALL)
        
        port_layout = QHBoxLayout()
        port_label = QLabel("Port")
        port_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        port_layout.addWidget(port_label)
        
        self.port_combo = QComboBox()
        self.port_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.port_combo.currentTextChanged.connect(self.update_monitor)
        port_layout.addWidget(self.port_combo)
        
        # Refresh port button
        self.refresh_button = QPushButton("⟳")
        self.refresh_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.refresh_button.setToolTip("Refresh Ports")
        self.refresh_button.clicked.connect(self.update_port_list)
        port_layout.addWidget(self.refresh_button)
        
        connection_layout.addLayout(port_layout)
        
        baud_layout = QHBoxLayout()
        baud_label = QLabel("Baud")
        baud_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        baud_layout.addWidget(baud_label)
        
        self.baud_combo = QComboBox()
        self.baud_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.baud_combo.addItems(['300', '1200', '2400', '4800', '9600', '19200', 
                                 '38400', '57600', '115200', '230400'])
        self.baud_combo.setCurrentText('9600')
        self.baud_combo.currentTextChanged.connect(self.update_monitor)
        baud_layout.addWidget(self.baud_combo)
        
        connection_layout.addLayout(baud_layout)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        self.connect_button.clicked.connect(self.toggle_connection)
        
        # Remove custom styling - use theme system
        connection_layout.addWidget(self.connect_button)
        
        # Add connection status indicator
        self.connection_status = QLabel("Status: Disconnected")
        self.connection_status.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        
        # Remove custom styling - use theme system
        connection_layout.addWidget(self.connection_status)
        
        top_layout.addWidget(connection_group, 1)
        
        # Sequence controls group
        sequence_group = QGroupBox("Command Sequences")
        sequence_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        sequence_layout = QVBoxLayout(sequence_group)
        self.scaler.spacing(sequence_layout, self.scaler.SPACING_SMALL)
        
        sequence_header = QLabel("Load and run predefined command sequences")
        sequence_header.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        sequence_layout.addWidget(sequence_header)
        
        sequence_combo_layout = QHBoxLayout()
        self.sequence_combo = QComboBox()
        self.sequence_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.update_sequence_combo()
        sequence_combo_layout.addWidget(self.sequence_combo, 1)
        
        self.run_sequence_button = QPushButton("▶ Run")
        self.run_sequence_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.run_sequence_button.clicked.connect(self.run_selected_sequence)
        sequence_combo_layout.addWidget(self.run_sequence_button)
        
        sequence_layout.addLayout(sequence_combo_layout)
        
        sequence_buttons_layout = QHBoxLayout()
        self.save_sequence_button = QPushButton("Save New")
        self.save_sequence_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.save_sequence_button.clicked.connect(self.save_new_sequence)
        sequence_buttons_layout.addWidget(self.save_sequence_button)
        
        self.delete_sequence_button = QPushButton("Delete")
        self.delete_sequence_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.delete_sequence_button.clicked.connect(self.delete_selected_sequence)
        sequence_buttons_layout.addWidget(self.delete_sequence_button)
        
        # Add export/import buttons
        self.export_sequences_button = QPushButton("Export All")
        self.export_sequences_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.export_sequences_button.clicked.connect(self.export_sequences)
        sequence_buttons_layout.addWidget(self.export_sequences_button)
        
        sequence_layout.addLayout(sequence_buttons_layout)
        
        top_layout.addWidget(sequence_group, 2)
        
        # Add the top panel to main splitter
        main_splitter.addWidget(top_panel)
        
        # Middle panel with I/O displays
        io_panel = QWidget()
        io_layout = QVBoxLayout(io_panel)
        self.scaler.spacing(io_layout, self.scaler.SPACING_MEDIUM)
        
        # Create a splitter for RX and TX displays - horizontal arrangement
        display_splitter = QSplitter(Qt.Orientation.Horizontal)
        display_splitter.setChildrenCollapsible(False)
        
        # RX Display with styled header (left panel)
        rx_panel = QWidget()
        rx_layout = QVBoxLayout(rx_panel)
        rx_layout.setContentsMargins(0, 0, 5, 0)  # Add a small right margin
        
        rx_header = QWidget()
        rx_header_layout = QHBoxLayout(rx_header)
        
        rx_title = QLabel("Incoming Data (RX)")
        rx_title.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        rx_header_layout.addWidget(rx_title)
        
        # Add RX stats display
        self.rx_stats_label = QLabel("0 B/s (0 bytes total)")
        self.rx_stats_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        rx_header_layout.addWidget(self.rx_stats_label)
        
        rx_header_layout.addStretch()
        
        # RX filter toggle
        self.filter_rx_toggle = QPushButton("Filter")
        self.filter_rx_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.filter_rx_toggle.setCheckable(True)
        self.filter_rx_toggle.setToolTip(
            "Filter Incoming Data\n\n"
            "When enabled, this filter:\n"
            "• Shows normal printable characters as-is\n"
            "• Preserves newlines, tabs, and carriage returns\n"
            "• Displays other non-printable characters as hex values [XX]\n\n"
            "Useful for protocols with binary data or control characters."
        )
        self.filter_rx_toggle.clicked.connect(self.toggle_rx_filter)
        rx_header_layout.addWidget(self.filter_rx_toggle)
        
        self.clear_rx_button = QPushButton("Clear")
        self.clear_rx_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.clear_rx_button.clicked.connect(self.clear_rx_display)
        rx_header_layout.addWidget(self.clear_rx_button)
        
        rx_layout.addWidget(rx_header)
        
        self.rx_display = QTextEdit()
        self.rx_display.setReadOnly(True)
        rx_layout.addWidget(self.rx_display)
        
        display_splitter.addWidget(rx_panel)
        
        # TX Display with styled header (right panel)
        tx_panel = QWidget()
        tx_layout = QVBoxLayout(tx_panel)
        tx_layout.setContentsMargins(5, 0, 0, 0)  # Add a small left margin
        
        tx_header = QWidget()
        tx_header_layout = QHBoxLayout(tx_header)
        
        tx_title = QLabel("Outgoing Data (TX)")
        tx_title.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        tx_header_layout.addWidget(tx_title)
        
        # Add TX stats display
        self.tx_stats_label = QLabel("0 B/s (0 bytes total)")
        self.tx_stats_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        tx_header_layout.addWidget(self.tx_stats_label)
        
        tx_header_layout.addStretch()
        
        self.clear_tx_button = QPushButton("Clear")
        self.clear_tx_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.clear_tx_button.clicked.connect(self.clear_tx_display)
        tx_header_layout.addWidget(self.clear_tx_button)
        
        tx_layout.addWidget(tx_header)
        
        self.tx_display = QTextEdit()
        self.tx_display.setReadOnly(True)
        tx_layout.addWidget(self.tx_display)
        
        display_splitter.addWidget(tx_panel)
        
        # Set initial sizes for display splitter - left (RX) wider than right (TX)
        display_splitter.setSizes([self.scaler.value(700), self.scaler.value(300)])
        
        io_layout.addWidget(display_splitter)
        
        # Add IO panel to main splitter
        main_splitter.addWidget(io_panel)
        
        # Bottom control panel - IMPROVED LAYOUT
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)
        self.scaler.spacing(bottom_layout, self.scaler.SPACING_SMALL)
        
        # Create a unified input and control row
        command_row = QHBoxLayout()
        self.scaler.spacing(command_row, self.scaler.SPACING_MEDIUM)
        
        # Left section: History button
        self.history_button = QPushButton("↑")
        self.history_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.history_button.setToolTip("Command History")
        self.history_button.clicked.connect(self.show_command_history)
        command_row.addWidget(self.history_button)
        
        # Center section: Input line with larger proportion
        self.input_line = QLineEdit()
        self.input_line.setFont(self.scaler.get_code_font())
        self.input_line.setPlaceholderText("Type command here...")
        self.input_line.returnPressed.connect(self.send_data)
        command_row.addWidget(self.input_line, 3)  # Give it more space proportion
        
        # Right section: Special keys and send button in a grouped layout
        keys_send_layout = QHBoxLayout()
        keys_send_layout.setSpacing(self.scaler.value(self.scaler.SPACING_SMALL))
        
        # Special keys directly in the layout
        self.enter_key = QPushButton("Enter")
        self.enter_key.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.enter_key.clicked.connect(lambda: self.send_special_key("Enter"))
        keys_send_layout.addWidget(self.enter_key)
        
        self.esc_key = QPushButton("Esc")
        self.esc_key.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.esc_key.clicked.connect(lambda: self.send_special_key("Escape"))
        keys_send_layout.addWidget(self.esc_key)
        
        # Send button - now adjacent to special keys
        self.send_button = QPushButton("Send")
        self.send_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        self.send_button.clicked.connect(self.send_data)
        keys_send_layout.addWidget(self.send_button)
        
        command_row.addLayout(keys_send_layout, 2)
        bottom_layout.addLayout(command_row)
        
        # Add command templates section
        templates_layout = self.add_command_templates()
        bottom_layout.addLayout(templates_layout)
        
        # Additional controls layout
        controls_panel = QWidget()
        controls_layout = QHBoxLayout(controls_panel)
        
        # Extended special keys section
        keys_group = QGroupBox("Special Keys")
        keys_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        keys_layout = QHBoxLayout(keys_group)
        self.scaler.spacing(keys_layout, self.scaler.SPACING_SMALL)
        
        self.backspace_key = QPushButton("⌫")
        self.backspace_key.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.backspace_key.setToolTip("Backspace")
        self.backspace_key.clicked.connect(lambda: self.send_special_key("Backspace"))
        keys_layout.addWidget(self.backspace_key)
        
        self.tab_key = QPushButton("⇥")
        self.tab_key.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.tab_key.setToolTip("Tab")
        self.tab_key.clicked.connect(lambda: self.send_special_key("Tab"))
        keys_layout.addWidget(self.tab_key)
        
        # Add Del and Space keys
        self.del_key = QPushButton("Del")
        self.del_key.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.del_key.setToolTip("Delete")
        self.del_key.clicked.connect(lambda: self.send_special_key("Delete"))
        keys_layout.addWidget(self.del_key)
        
        self.space_key = QPushButton("Space")
        self.space_key.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.space_key.clicked.connect(lambda: self.send_special_key("Space"))
        keys_layout.addWidget(self.space_key)
        
        controls_layout.addWidget(keys_group, 1)
        
        # Toggle switches section
        toggle_group = QGroupBox("Display Options")
        toggle_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        toggle_layout = QHBoxLayout(toggle_group)
        self.scaler.spacing(toggle_layout, self.scaler.SPACING_SMALL)
        
        self.timestamp_toggle = QPushButton("Timecode")
        self.timestamp_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.timestamp_toggle.setCheckable(True)
        self.timestamp_toggle.clicked.connect(self.toggle_timestamp)
        toggle_layout.addWidget(self.timestamp_toggle)
        
        self.hex_toggle = QPushButton("Hex Mode")
        self.hex_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.hex_toggle.setCheckable(True)
        self.hex_toggle.clicked.connect(self.toggle_hex)
        toggle_layout.addWidget(self.hex_toggle)
        
        self.raw_mode_toggle = QPushButton("Auto-Term")
        self.raw_mode_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.raw_mode_toggle.setCheckable(True)
        self.raw_mode_toggle.setChecked(True)
        self.raw_mode_toggle.clicked.connect(self.toggle_raw_mode)
        toggle_layout.addWidget(self.raw_mode_toggle)
        
        self.auto_clear_toggle = QPushButton("Auto-Clear")
        self.auto_clear_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.auto_clear_toggle.setCheckable(True)
        self.auto_clear_toggle.setChecked(self.auto_clear_rx)
        self.auto_clear_toggle.clicked.connect(self.toggle_auto_clear)
        toggle_layout.addWidget(self.auto_clear_toggle)
        
        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.clear_all_button.clicked.connect(self.clear_all_displays)
        toggle_layout.addWidget(self.clear_all_button)
        
        controls_layout.addWidget(toggle_group, 2)
        
        bottom_layout.addWidget(controls_panel)
        
        # Add the bottom panel to main splitter
        main_splitter.addWidget(bottom_panel)
        
        # Set initial sizes for main splitter sections - maximize central display area
        main_splitter.setSizes([self.scaler.value(120), self.scaler.value(550), self.scaler.value(130)])
        
        # Add main splitter to layout
        main_layout.addWidget(main_splitter)
        
        # Store command history
        self.command_history = []
        self.history_index = -1
        
        # Set up key press event for command history navigation
        self.input_line.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle key events for command history navigation."""
        from PyQt6.QtCore import QEvent
        
        if obj is self.input_line and event.type() == QEvent.Type.KeyPress:
            # Use the event directly, it's already a QKeyEvent
            
            # Up arrow key - previous command
            if event.key() == Qt.Key.Key_Up:
                self.navigate_history(-1)
                return True
                
            # Down arrow key - next command
            elif event.key() == Qt.Key.Key_Down:
                self.navigate_history(1)
                return True
                
        # Pass event to parent class
        return super().eventFilter(obj, event)
    
    def navigate_history(self, direction):
        """Navigate through command history."""
        if not self.command_history:
            return
            
        new_index = self.history_index + direction
        
        if new_index < 0:
            new_index = 0
        elif new_index >= len(self.command_history):
            new_index = len(self.command_history) - 1
            
        if new_index != self.history_index and 0 <= new_index < len(self.command_history):
            self.history_index = new_index
            self.input_line.setText(self.command_history[self.history_index])
            # Place cursor at the end of text
            self.input_line.setCursorPosition(len(self.input_line.text()))
    
    def show_command_history(self):
        """Show command history in a popup dialog."""
        if not self.command_history:
            QMessageBox.information(self, "Command History", "No commands in history.")
            return
            
        # Create a simple dialog to display history
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Command History")
        dialog.setIcon(QMessageBox.Icon.Information)
        
        # Format history items
        history_text = "Recent commands (newest first):\n\n"
        for cmd in reversed(self.command_history[-20:]):  # Show last 20 commands
            history_text += f"• {cmd}\n"
            
        dialog.setText(history_text)
        dialog.exec()
    
    def setup_fonts(self):
        """Set up fonts with proper scaling."""
        # Get consistent fonts from scaler
        code_font = self.scaler.get_code_font()
        
        # Apply to text displays
        self.rx_display.setFont(code_font)
        self.tx_display.setFont(code_font)
    
    def setup_command_completer(self):
        """Setup auto-completion for common commands."""
        # Build a list of common commands from history or predefined list
        common_commands = [
            "AT", "AT+RESET", "AT+VERSION", "AT+INFO", "AT+STATUS",
            "GET", "SET", "READ", "WRITE", "HELP", "ECHO", "REBOOT"
        ]
        
        # Add commands from history if available
        if self.command_history:
            common_commands.extend(self.command_history)
            # Remove duplicates while preserving order
            common_commands = list(dict.fromkeys(common_commands))
        
        # Create and configure completer
        completer = QCompleter(common_commands)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.input_line.setCompleter(completer)
    
    def add_command_templates(self):
        """Add common command templates feature."""
        # Create a drop-down for quick command templates
        templates_layout = QHBoxLayout()
        
        templates_label = QLabel("Templates:")
        templates_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        templates_layout.addWidget(templates_label)
        
        self.templates_combo = QComboBox()
        self.templates_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.templates_combo.addItem("-- Select Template --")
        
        # Add common command templates for various devices
        common_templates = {
            "AT Commands": ["AT", "AT+RST", "AT+GMR", "AT+CWLAP", "AT+CWJAP?"],
            "Network": ["ping 8.8.8.8", "ifconfig", "ipconfig", "netstat"],
            "Custom": []  # User can add custom templates
        }
        
        # Add to combo box
        for category, commands in common_templates.items():
            self.templates_combo.addItem(f"--- {category} ---")
            for cmd in commands:
                self.templates_combo.addItem(cmd)
        
        # Connect signal
        self.templates_combo.currentTextChanged.connect(self.apply_template)
        templates_layout.addWidget(self.templates_combo, 1)
        
        # Add button to save current command as template
        save_template_btn = QPushButton("+")
        save_template_btn.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        save_template_btn.setToolTip("Save current command as template")
        save_template_btn.clicked.connect(self.save_as_template)
        templates_layout.addWidget(save_template_btn)
        
        return templates_layout

    def apply_template(self, template):
        """Apply selected command template to input line."""
        if (template != "-- Select Template --" and 
            not template.startswith("--- ") and 
            not template.endswith(" ---")):
            self.input_line.setText(template)
            self.input_line.setFocus()
            # Reset selection after applying
            self.templates_combo.setCurrentIndex(0)

    def save_as_template(self):
        """Save current command as a template."""
        current_text = self.input_line.text().strip()
        if not current_text:
            return
            
        # Prompt for category
        categories = ["Custom", "AT Commands", "Network", "New Category..."]
        category, ok = QInputDialog.getItem(
            self, "Save Template", 
            "Select category:", categories, 0, False
        )
        
        if not ok:
            return
            
        # Handle new category
        if category == "New Category...":
            category, ok = QInputDialog.getText(
                self, "New Category", "Enter category name:"
            )
            if not ok or not category:
                return
        
        # Add to templates combo box
        # In a real implementation, you'd save this to a configuration file
        if current_text not in [self.templates_combo.itemText(i) 
                              for i in range(self.templates_combo.count())]:
            # Add category header if it doesn't exist
            cat_text = f"--- {category} ---"
            if cat_text not in [self.templates_combo.itemText(i) 
                              for i in range(self.templates_combo.count())]:
                self.templates_combo.addItem(cat_text)
                
            # Add the template
            self.templates_combo.addItem(current_text)
            self.status_message.emit(f"Added template: {current_text}", 0)
    
    def update_port_list(self):
        """Update the list of available serial ports."""
        import serial.tools.list_ports
        
        current_port = self.port_combo.currentText()
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # Add port with description for better user information
            display_text = f"{port.device} ({port.description})"
            self.port_combo.addItem(display_text, port.device)
        
        # Restore previous selection if it still exists
        for i in range(self.port_combo.count()):
            if self.port_combo.itemData(i) == current_port:
                self.port_combo.setCurrentIndex(i)
                break
        
        self.status_message.emit(f"Found {len(ports)} serial ports", 3000)
        
    def update_monitor(self):
        """Update serial monitor settings based on current UI selections."""
        if self.monitor:
            self.monitor.stop()
            if self.serial_thread:
                self.serial_thread.quit()
                self.serial_thread.wait()
        
        # Get actual port from currentData (not display text)
        port = self.port_combo.currentData()
        baudrate = int(self.baud_combo.currentText())
        if port:
            # Pass auto_termination state to new monitor instance
            auto_term = True
            if hasattr(self, 'raw_mode_toggle'):
                auto_term = self.raw_mode_toggle.isChecked()
                
            self.monitor = SerialMonitor(
                port=port, 
                baudrate=baudrate, 
                timestamp=self.timestamp_toggle.isChecked(),
                auto_termination=auto_term
            )
            
            # Initialize statistics
            self.monitor.stats = {
                'rx_bytes': 0,
                'tx_bytes': 0
            }
            
            self.setup_serial_thread()
            self.update_status()
    
    def toggle_connection(self):
        """Toggle serial connection state."""
        if not self.monitor:
            self.update_monitor()
        
        if self.monitor and self.monitor.ser and self.monitor.ser.is_open:
            self.monitor.stop()
            self.connect_button.setText("Connect")
            self.connect_button.setChecked(False)
            self.connection_status.setText("Status: Disconnected")
        else:
            if self.monitor and self.monitor.start():
                self.connect_button.setText("Disconnect")
                self.connect_button.setChecked(True)
                self.connection_status.setText("Status: Connected")
        self.update_status()
    
    def setup_serial_thread(self):
        """Set up the thread for asynchronous serial operations."""
        self.serial_thread = SerialThread(self.monitor)
        self.serial_thread.data_received.connect(self.update_rx_display)
        self.serial_thread.error_occurred.connect(self.handle_error)
        self.serial_thread.start()
    
    def update_rx_display(self, text):
        """Update the RX display with received data."""
        # Update byte count for statistics
        self.rx_bytes += len(text)
        if hasattr(self.monitor, 'stats'):
            self.monitor.stats['rx_bytes'] = self.rx_bytes
        
        # Apply filtering if enabled
        if hasattr(self, 'filter_rx_toggle') and self.filter_rx_toggle.isChecked():
            # Simple filter: only show printable ASCII and common control chars
            filtered_text = ""
            for c in text:
                if 32 <= ord(c) <= 126 or c in '\r\n\t':
                    filtered_text += c
                else:
                    filtered_text += f"[{ord(c):02X}]"
            text = filtered_text
        
        if self.monitor.hex_display:
            text = ' '.join(f'{ord(c):02X}' for c in text)
        if self.monitor.timestamp:
            text = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {text}"

        cursor = self.rx_display.textCursor()
        format = QTextCharFormat()
        # Use default text color from Fusion theme
        cursor.setCharFormat(format)
        cursor.insertText(f"[RX] {text}\n")
        self.rx_display.setTextCursor(cursor)
        self.rx_display.ensureCursorVisible()
    
    def send_data(self):
        """Send data to the serial port with visual feedback."""
        if not self.monitor or not self.monitor.ser or not self.monitor.ser.is_open:
            self.handle_error("Not connected")
            return
            
        # Clear RX display if auto-clear is enabled
        if self.auto_clear_rx:
            self.clear_rx_display()
            
        text = self.input_line.text().strip()
        if text:
            # Save to command history
            if not self.command_history or self.command_history[-1] != text:
                self.command_history.append(text)
                self.history_index = len(self.command_history)
                
                # Update completer
                self.setup_command_completer()
            
            # Visual feedback - briefly disable the input and change button appearance
            self.input_line.setEnabled(False)
            self.send_button.setText("Sending...")
            
            # Use a timer to restore the UI after a short delay
            QTimer.singleShot(150, self.restore_send_ui)
            
            # Continue with data sending
            sent_data = self.monitor.send_data(text)
            if sent_data:
                # Update byte count for statistics
                self.tx_bytes += len(sent_data)
                if hasattr(self.monitor, 'stats'):
                    self.monitor.stats['tx_bytes'] = self.tx_bytes
                
                display_text = text
                if self.monitor.hex_display:
                    display_text = ' '.join(f'{b:02X}' for b in sent_data)
                if self.monitor.timestamp:
                    display_text = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {display_text}"

                cursor = self.tx_display.textCursor()
                format = QTextCharFormat()
                # Use default text color from Fusion theme
                cursor.setCharFormat(format)
                cursor.insertText(f"[TX] {display_text}\n")
                self.tx_display.setTextCursor(cursor)
                self.tx_display.ensureCursorVisible()
            self.input_line.clear()
    
    def restore_send_ui(self):
        """Restore UI after send operation."""
        self.input_line.setEnabled(True)
        self.input_line.setFocus()
        self.send_button.setText("Send")
    
    def send_special_key(self, key):
        """Send a special key directly to the serial connection."""
        if not self.monitor or not self.monitor.ser or not self.monitor.ser.is_open:
            self.handle_error("Not connected")
            return
        
        # Clear RX display if auto-clear is enabled
        if self.auto_clear_rx:
            self.clear_rx_display()
            
        # Visual feedback for key press
        button = None
        if key == "Enter":
            button = self.enter_key
        elif key == "Escape":
            button = self.esc_key
        elif key == "Backspace":
            button = self.backspace_key
        elif key == "Tab":
            button = self.tab_key
        elif key == "Delete":
            button = self.del_key
        elif key == "Space":
            button = self.space_key
            
        if button:
            # Visual feedback handled by Fusion style on button press
            pass
            
        sent_data = self.monitor.send_key(key)
        if sent_data:
            # Update byte count for statistics
            self.tx_bytes += len(sent_data)
            if hasattr(self.monitor, 'stats'):
                self.monitor.stats['tx_bytes'] = self.tx_bytes
            
            # Display the key press in the TX display
            cursor = self.tx_display.textCursor()
            format = QTextCharFormat()
            # Use default text color from Fusion theme
            cursor.setCharFormat(format)
            cursor.insertText(f"[KEY] {key}\n")
            self.tx_display.setTextCursor(cursor)
            self.tx_display.ensureCursorVisible()
    
    def toggle_timestamp(self):
        """Toggle timestamp display."""
        if self.monitor:
            self.monitor.timestamp = not self.monitor.timestamp
            if self.monitor.timestamp:
                self.timestamp_toggle.setChecked(True)
                self.status_message.emit("Timestamp display: ON", 3000)
            else:
                self.timestamp_toggle.setChecked(False)
                self.status_message.emit("Timestamp display: OFF", 3000)
    
    def toggle_hex(self):
        """Toggle hex display mode."""
        if self.monitor:
            self.monitor.hex_display = not self.monitor.hex_display
            if self.monitor.hex_display:
                self.hex_toggle.setChecked(True)
                self.status_message.emit("HEX display mode: ON", 3000)
            else:
                self.hex_toggle.setChecked(False)
                self.status_message.emit("HEX display mode: OFF", 3000)
    
    def toggle_raw_mode(self):
        """Toggle raw mode (whether termination chars are auto-added)."""
        if self.monitor:
            self.monitor.auto_termination = not self.monitor.auto_termination
            if self.monitor.auto_termination:
                self.raw_mode_toggle.setChecked(True)
                self.status_message.emit("Auto-termination: ON", 3000)
            else:
                self.raw_mode_toggle.setChecked(False)
                self.status_message.emit("Auto-termination: OFF (Raw Mode)", 3000)
    
    def toggle_auto_clear(self):
        """Toggle auto-clear of RX display on new command."""
        self.auto_clear_rx = not self.auto_clear_rx
        if self.auto_clear_rx:
            self.auto_clear_toggle.setChecked(True)
            self.status_message.emit("Auto-clear RX on command: ENABLED", 3000)
        else:
            self.auto_clear_toggle.setChecked(False)
            self.status_message.emit("Auto-clear RX on command: DISABLED", 3000)
    
    def toggle_rx_filter(self):
        """Toggle filtering of non-printable characters in RX display."""
        if self.filter_rx_toggle.isChecked():
            self.status_message.emit("RX filtering: ENABLED", 3000)
        else:
            self.status_message.emit("RX filtering: DISABLED", 3000)
    
    def clear_rx_display(self):
        """Clear the RX display window."""
        self.rx_display.clear()
        self.status_message.emit("RX display cleared", 3000)
    
    def clear_tx_display(self):
        """Clear the TX display window."""
        self.tx_display.clear()
        self.status_message.emit("TX display cleared", 3000)
    
    def clear_all_displays(self):
        """Clear both RX and TX display windows."""
        self.rx_display.clear()
        self.tx_display.clear()
        self.status_message.emit("All displays cleared", 3000)
    
    def update_status(self):
        """Update connection status in parent window."""
        # Emit status to parent window
        port = self.port_combo.currentData() or "N/A"
        baud = self.baud_combo.currentText()
        status = "ONLINE" if self.monitor and self.monitor.ser and self.monitor.ser.is_open else "OFFLINE"
        
        # Update button appearance based on connection status
        if status == "ONLINE":
            self.connect_button.setText("Disconnect")
            self.connect_button.setChecked(True)
            self.connection_status.setText("Status: Connected")
            
            # Remove custom styling - use theme system
        else:
            self.connect_button.setText("Connect")
            self.connect_button.setChecked(False)
            self.connection_status.setText("Status: Disconnected")
            
            # Remove custom styling - use theme system
        
        # Emit connection info to parent
        self.status_message.emit(f"PORT: {port} | BAUD: {baud} | STATUS: {status}", 0)
    
    def handle_error(self, message):
        """Handle error messages and update UI."""
        self.error_occurred.emit(message)
        
        # Make errors more visible in RX display
        cursor = self.rx_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        format = QTextCharFormat()
        # Use default text color from Fusion theme
        cursor.setCharFormat(format)
        cursor.insertText(f"[ERROR] {message}\n")
        self.rx_display.setTextCursor(cursor)
        self.rx_display.ensureCursorVisible()
        
        # Provide visual feedback
        QTimer.singleShot(100, lambda: self.flash_error_indicator(message))
    
    def flash_error_indicator(self, message):
        """Flash an error message in the status bar."""
        # This is just a placeholder - in a real implementation, 
        # you might create a temporary overlay or animation
        self.status_message.emit(f"ERROR: {message}", 5000)
        
        # Restore UI if needed
        if not self.input_line.isEnabled():
            self.restore_send_ui()
    
    def update_stats(self):
        """Update RX/TX statistics display."""
        # Calculate data rates
        now = datetime.now()
        time_diff = (now - self.last_time).total_seconds()
        
        if time_diff > 0:
            # RX rate
            rx_diff = self.rx_bytes - self.last_rx
            rx_rate = rx_diff / time_diff
            
            # TX rate
            tx_diff = self.tx_bytes - self.last_tx
            tx_rate = tx_diff / time_diff
            
            # Format for display
            if rx_rate < 1024:
                rx_rate_str = f"{rx_rate:.1f} B/s"
            else:
                rx_rate_str = f"{rx_rate/1024:.1f} KB/s"
                
            if tx_rate < 1024:
                tx_rate_str = f"{tx_rate:.1f} B/s"
            else:
                tx_rate_str = f"{tx_rate/1024:.1f} KB/s"
            
            # Update labels with improved formatting
            self.rx_stats_label.setText(f"{rx_rate_str} ({self.rx_bytes} bytes total)")
            self.tx_stats_label.setText(f"{tx_rate_str} ({self.tx_bytes} bytes total)")
            
            # Store values for next calculation
            self.last_rx = self.rx_bytes
            self.last_tx = self.tx_bytes
            self.last_time = now
    
    def update_sequence_combo(self):
        """Update the sequence combo box with current sequences."""
        self.sequence_combo.clear()
        self.sequence_combo.addItem("-- Select Sequence --")
        for name in sorted(self.command_sequences.keys()):
            self.sequence_combo.addItem(name)
    
    def load_sequences(self):
        """Load command sequences from disk."""
        try:
            for filename in os.listdir(self.sequences_dir):
                if filename.endswith('.json'):
                    with open(os.path.join(self.sequences_dir, filename), 'r') as f:
                        data = json.load(f)
                        sequence = CommandSequence.from_dict(data)
                        self.command_sequences[sequence.name] = sequence
        except Exception as e:
            print(f"Error loading sequences: {e}")
    
    def save_new_sequence(self):
        """Save the current command history as a new sequence."""
        # Get last 10 commands from TX display
        tx_text = self.tx_display.toPlainText()
        lines = tx_text.splitlines()
        
        # Filter for command lines
        tx_lines = [line for line in lines if line.startswith('[TX]')]
        last_commands = tx_lines[-10:] if len(tx_lines) > 10 else tx_lines
        
        if not last_commands:
            self.handle_error("No commands to save")
            return
        
        # Extract commands
        commands = []
        for line in last_commands:
            # Strip timestamp and [TX] prefix
            cmd_text = line
            if ']' in line:
                cmd_text = line.split(']', 1)[1].strip()
            if cmd_text.startswith('[TX]'):
                cmd_text = cmd_text[4:].strip()
            
            commands.append({
                'command': cmd_text,
                'delay': 500,  # Default 500ms delay
                'wait_for_prompt': False
            })
        
        # Show dialog to edit sequence
        name, ok = QInputDialog.getText(self, "Save Sequence", "Sequence Name:")
        if ok and name:
            sequence = CommandSequence(name, commands)
            
            # Save to file
            filename = os.path.join(self.sequences_dir, f"{name}.json")
            with open(filename, 'w') as f:
                json.dump(sequence.to_dict(), f, indent=2)
            
            # Add to memory
            self.command_sequences[name] = sequence
            self.update_sequence_combo()
            self.sequence_combo.setCurrentText(name)
            self.status_message.emit(f"Saved sequence: {name}", 3000)
    
    def delete_selected_sequence(self):
        """Delete the currently selected sequence."""
        name = self.sequence_combo.currentText()
        if name and name != "-- Select Sequence --":
            # Confirm deletion
            confirm = QMessageBox.question(
                self, "Delete Sequence", 
                f"Are you sure you want to delete '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if confirm == QMessageBox.StandardButton.Yes:
                # Remove from memory
                if name in self.command_sequences:
                    del self.command_sequences[name]
                
                # Remove from disk
                filename = os.path.join(self.sequences_dir, f"{name}.json")
                if os.path.exists(filename):
                    os.remove(filename)
                
                self.update_sequence_combo()
                self.status_message.emit(f"Deleted sequence: {name}", 3000)
    
    def export_sequences(self):
        """Export all command sequences to a JSON file."""
        if not self.command_sequences:
            self.status_message.emit("No sequences to export", 3000)
            return
            
        # Ask for file location
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export All Sequences", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        # Ensure file has .json extension
        if not file_path.lower().endswith('.json'):
            file_path += '.json'
            
        try:
            # Export all sequences in one file
            export_data = {}
            for name, sequence in self.command_sequences.items():
                export_data[name] = sequence.to_dict()
                
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
                
            self.status_message.emit(f"Exported {len(export_data)} sequences to {file_path}", 3000)
        except Exception as e:
            self.error_occurred.emit(f"Error exporting sequences: {str(e)}")
    
    def run_selected_sequence(self):
        """Run the currently selected command sequence."""
        name = self.sequence_combo.currentText()
        if name and name != "-- Select Sequence --" and name in self.command_sequences:
            # Reset sequence
            sequence = self.command_sequences[name]
            sequence.reset()
            
            # Store as current sequence
            self.current_sequence = sequence
            
            # Visual feedback
            self.status_message.emit(f"Running sequence: {name}", 3000)
            self.run_sequence_button.setText("▶ Running...")
            self.run_sequence_button.setEnabled(False)
            
            # Start execution
            self.execute_next_sequence_step()
    
    def execute_next_sequence_step(self):
        """Execute the next step in the current sequence."""
        if not self.current_sequence:
            return
            
        # Get next command
        cmd_info = self.current_sequence.get_next_command()
        if not cmd_info:
            self.status_message.emit(f"Sequence '{self.current_sequence.name}' completed", 3000)
            self.current_sequence = None
            self.run_sequence_button.setText("▶ Run")
            self.run_sequence_button.setEnabled(True)
            return
        
        # Send the command
        command = cmd_info['command']
        
        # Show what we're doing
        self.status_message.emit(f"Sending: {command}", 1000)
        
        # Clear RX display if auto-clear is enabled
        if self.auto_clear_rx:
            self.clear_rx_display()
        
        # Send without auto-termination if needed
        original_auto_term = self.monitor.auto_termination
        if 'use_termination' in cmd_info:
            self.monitor.auto_termination = cmd_info['use_termination']
        
        if command.startswith('[KEY]'):
            # Special key
            key = command[5:].strip()
            self.send_special_key(key)
        else:
            # Regular command
            self.input_line.setText(command)
            self.send_data()
        
        # Restore auto termination setting
        self.monitor.auto_termination = original_auto_term
        
        # Schedule next command after delay
        delay = cmd_info.get('delay', 500)  # Default 500ms
        QTimer.singleShot(delay, self.execute_next_sequence_step)