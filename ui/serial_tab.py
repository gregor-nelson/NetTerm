"""
Enhanced Serial Monitor tab UI component with simplified layout.
"""
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                           QLineEdit, QPushButton, QLabel, QComboBox, 
                           QInputDialog, QMessageBox, QGroupBox, QSplitter,
                           QFrame, QCompleter)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QFont

from core.serial_monitor import SerialMonitor
from core.serial_thread import SerialThread


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
        self.auto_clear_rx = True  # Flag for auto-clearing RX on command
        
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
        
        # Top Section: Two rows of controls
        top_section = QVBoxLayout()
        self.scaler.spacing(top_section, self.scaler.SPACING_SMALL)
        
        # First row: Connection, Settings, Actions
        first_row = QHBoxLayout()
        self.scaler.spacing(first_row, self.scaler.SPACING_MEDIUM)
        
        # Connection controls group
        connection_group = QGroupBox("Connection")
        connection_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        connection_layout = QHBoxLayout(connection_group)
        self.scaler.spacing(connection_layout, self.scaler.SPACING_SMALL)
        
        # Port selection
        port_label = QLabel("Port:")
        port_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        connection_layout.addWidget(port_label)
        
        self.port_combo = QComboBox()
        self.port_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.port_combo.currentTextChanged.connect(self.update_monitor)
        connection_layout.addWidget(self.port_combo)
        
        # Refresh port button
        self.refresh_button = QPushButton("⟳")
        self.refresh_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.refresh_button.setToolTip("Refresh Ports")
        self.refresh_button.clicked.connect(self.update_port_list)
        connection_layout.addWidget(self.refresh_button)
        
        # Baud rate
        baud_label = QLabel("Baud:")
        baud_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        connection_layout.addWidget(baud_label)
        
        self.baud_combo = QComboBox()
        self.baud_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.baud_combo.addItems(['300', '1200', '2400', '4800', '9600', '19200', 
                                 '38400', '57600', '115200', '230400'])
        self.baud_combo.setCurrentText('9600')
        self.baud_combo.currentTextChanged.connect(self.update_monitor)
        connection_layout.addWidget(self.baud_combo)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        self.connect_button.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(self.connect_button)
        
        first_row.addWidget(connection_group)
        
        # Serial settings group
        settings_group = QGroupBox("Settings")
        settings_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        settings_layout = QHBoxLayout(settings_group)
        self.scaler.spacing(settings_layout, self.scaler.SPACING_SMALL)
        
        # Toggle switches
        self.timestamp_toggle = QPushButton("Timecode")
        self.timestamp_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.timestamp_toggle.setCheckable(True)
        self.timestamp_toggle.clicked.connect(self.toggle_timestamp)
        settings_layout.addWidget(self.timestamp_toggle)
        
        self.hex_toggle = QPushButton("Hex Mode")
        self.hex_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.hex_toggle.setCheckable(True)
        self.hex_toggle.clicked.connect(self.toggle_hex)
        settings_layout.addWidget(self.hex_toggle)
        
        self.raw_mode_toggle = QPushButton("Auto-Term")
        self.raw_mode_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.raw_mode_toggle.setCheckable(True)
        self.raw_mode_toggle.setChecked(True)
        self.raw_mode_toggle.clicked.connect(self.toggle_raw_mode)
        settings_layout.addWidget(self.raw_mode_toggle)
        
        self.auto_clear_toggle = QPushButton("Auto-Clear")
        self.auto_clear_toggle.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.auto_clear_toggle.setCheckable(True)
        self.auto_clear_toggle.setChecked(self.auto_clear_rx)
        self.auto_clear_toggle.clicked.connect(self.toggle_auto_clear)
        settings_layout.addWidget(self.auto_clear_toggle)
        
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
        settings_layout.addWidget(self.filter_rx_toggle)
        
        first_row.addWidget(settings_group)
        
        top_section.addLayout(first_row)
        
        # Second row: Actions and Command Input
        second_row = QHBoxLayout()
        self.scaler.spacing(second_row, self.scaler.SPACING_MEDIUM)
        
        # Actions group (moved from first row)
        actions_group = QGroupBox("Actions")
        actions_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        actions_layout = QHBoxLayout(actions_group)
        self.scaler.spacing(actions_layout, self.scaler.SPACING_SMALL)
        
        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.clear_all_button.clicked.connect(self.clear_all_displays)
        actions_layout.addWidget(self.clear_all_button)
        
        # History button
        self.history_button = QPushButton("History")
        self.history_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.history_button.setToolTip("Command History")
        self.history_button.clicked.connect(self.show_command_history)
        actions_layout.addWidget(self.history_button)
        
        # Special keys
        self.enter_key = QPushButton("Enter")
        self.enter_key.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.enter_key.clicked.connect(lambda: self.send_special_key("Enter"))
        actions_layout.addWidget(self.enter_key)
        
        self.esc_key = QPushButton("Esc")
        self.esc_key.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.esc_key.clicked.connect(lambda: self.send_special_key("Escape"))
        actions_layout.addWidget(self.esc_key)
        
        second_row.addWidget(actions_group)
        
        # Command input group
        command_group = QGroupBox("Command Input")
        command_group.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        command_layout = QHBoxLayout(command_group)
        self.scaler.spacing(command_layout, self.scaler.SPACING_SMALL)
        
        self.input_line = QLineEdit()
        self.input_line.setFont(self.scaler.get_code_font())
        self.input_line.setPlaceholderText("Type command here...")
        self.input_line.returnPressed.connect(self.send_data)
        command_layout.addWidget(self.input_line, 1)
        
        self.send_button = QPushButton("Send")
        self.send_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        self.send_button.clicked.connect(self.send_data)
        command_layout.addWidget(self.send_button)
        
        second_row.addWidget(command_group, 1)
        
        top_section.addLayout(second_row)
        
        main_layout.addLayout(top_section)
        
        # Bottom Section: TX/RX displays with splitter
        display_splitter = QSplitter(Qt.Orientation.Horizontal)
        display_splitter.setChildrenCollapsible(False)
        
        # TX Display (left panel)
        tx_panel = QWidget()
        tx_layout = QVBoxLayout(tx_panel)
        tx_layout.setContentsMargins(0, 0, 5, 0)
        
        tx_header = QWidget()
        tx_header_layout = QHBoxLayout(tx_header)
        
        tx_title = QLabel("Transmitted Data (TX)")
        tx_title.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        tx_header_layout.addWidget(tx_title)
        
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
        
        # RX Display (right panel)
        rx_panel = QWidget()
        rx_layout = QVBoxLayout(rx_panel)
        rx_layout.setContentsMargins(5, 0, 0, 0)
        
        rx_header = QWidget()
        rx_header_layout = QHBoxLayout(rx_header)
        
        rx_title = QLabel("Received Data (RX)")
        rx_title.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        rx_header_layout.addWidget(rx_title)
        
        rx_header_layout.addStretch()
        
        self.clear_rx_button = QPushButton("Clear")
        self.clear_rx_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.clear_rx_button.clicked.connect(self.clear_rx_display)
        rx_header_layout.addWidget(self.clear_rx_button)
        
        rx_layout.addWidget(rx_header)
        
        self.rx_display = QTextEdit()
        self.rx_display.setReadOnly(True)
        rx_layout.addWidget(self.rx_display)
        
        display_splitter.addWidget(rx_panel)
        
        # Set initial sizes for display splitter - equal sizes
        display_splitter.setSizes([self.scaler.value(500), self.scaler.value(500)])
        
        main_layout.addWidget(display_splitter, 1)
        
        # Bottom Statistics Status Bar
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.Shape.NoFrame)
        stats_frame_layout = QHBoxLayout(stats_frame)
        self.scaler.spacing(stats_frame_layout, self.scaler.SPACING_SMALL)
        self.scaler.margins(stats_frame_layout, self.scaler.SPACING_SMALL, self.scaler.SPACING_SMALL, self.scaler.SPACING_SMALL, self.scaler.SPACING_SMALL)
        
        # Statistics labels in horizontal layout
        self.rx_stats_label = QLabel("RX: 0 B/s (0 bytes)")
        self.rx_stats_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        stats_frame_layout.addWidget(self.rx_stats_label)
        
        # Separator
        separator1 = QLabel(" | ")
        separator1.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        stats_frame_layout.addWidget(separator1)
        
        self.tx_stats_label = QLabel("TX: 0 B/s (0 bytes)")
        self.tx_stats_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        stats_frame_layout.addWidget(self.tx_stats_label)
        
        # Separator
        separator2 = QLabel(" | ")
        separator2.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        stats_frame_layout.addWidget(separator2)
        
        # Connection status
        self.connection_status = QLabel("Status: Disconnected")
        self.connection_status.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        stats_frame_layout.addWidget(self.connection_status)
        
        # Stretch to push everything to the left
        stats_frame_layout.addStretch()
        
        main_layout.addWidget(stats_frame)
        
        # Store command history
        self.command_history = []
        self.history_index = -1
        
        # Set up key press event for command history navigation
        self.input_line.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle key events for command history navigation."""
        from PyQt6.QtCore import QEvent
        
        if obj is self.input_line and event.type() == QEvent.Type.KeyPress:
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
            
        sent_data = self.monitor.send_key(key)
        if sent_data:
            # Update byte count for statistics
            self.tx_bytes += len(sent_data)
            if hasattr(self.monitor, 'stats'):
                self.monitor.stats['tx_bytes'] = self.tx_bytes
            
            # Display the key press in the TX display
            cursor = self.tx_display.textCursor()
            format = QTextCharFormat()
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
        else:
            self.connect_button.setText("Connect")
            self.connect_button.setChecked(False)
            self.connection_status.setText("Status: Disconnected")
        
        # Emit connection info to parent
        self.status_message.emit(f"PORT: {port} | BAUD: {baud} | STATUS: {status}", 0)
    
    def handle_error(self, message):
        """Handle error messages and update UI."""
        self.error_occurred.emit(message)
        
        # Make errors more visible in RX display
        cursor = self.rx_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        format = QTextCharFormat()
        cursor.setCharFormat(format)
        cursor.insertText(f"[ERROR] {message}\n")
        self.rx_display.setTextCursor(cursor)
        self.rx_display.ensureCursorVisible()
        
        # Provide visual feedback
        QTimer.singleShot(100, lambda: self.flash_error_indicator(message))
    
    def flash_error_indicator(self, message):
        """Flash an error message in the status bar."""
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
            self.rx_stats_label.setText(f"RX: {rx_rate_str} ({self.rx_bytes} bytes)")
            self.tx_stats_label.setText(f"TX: {tx_rate_str} ({self.tx_bytes} bytes)")
            
            # Store values for next calculation
            self.last_rx = self.rx_bytes
            self.last_tx = self.tx_bytes
            self.last_time = now