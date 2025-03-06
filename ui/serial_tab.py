"""
Serial Monitor tab UI component.
"""
import os
import json
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                           QLineEdit, QPushButton, QLabel, QComboBox, 
                           QInputDialog, QMessageBox)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QFont

from core.serial_monitor import SerialMonitor
from core.serial_thread import SerialThread
from core.command_sequence import CommandSequence


class SerialTab(QWidget):
    """Serial Monitor tab UI component."""
    
    # Define signals for communication with parent
    status_message = pyqtSignal(str, int)  # message, timeout
    error_occurred = pyqtSignal(str)
    
    def __init__(self, ui_scaler, parent=None):
        """
        Initialize the Serial tab component.
        
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
        self.update_port_list()
    
    def init_ui(self):
        """Initialize the Serial Monitor tab UI."""
        serial_layout = QVBoxLayout(self)
        self.scaler.spacing(serial_layout, 10)
        self.scaler.margins(serial_layout, 10, 10, 10, 10)

        # Top control panel
        control_panel = QWidget()
        control_panel.setObjectName("controlPanel")
        control_layout = QHBoxLayout(control_panel)
        self.scaler.margins(control_layout, 10, 10, 10, 10)
        
        # Connection controls group
        connection_group = QWidget()
        connection_group.setObjectName("connectionGroup")
        connection_layout = QVBoxLayout(connection_group)
        self.scaler.spacing(connection_layout, 8)
        
        port_layout = QHBoxLayout()
        port_label = QLabel("PORT")
        port_label.setObjectName("sectionLabel")
        port_layout.addWidget(port_label)
        
        self.port_combo = QComboBox()
        self.port_combo.currentTextChanged.connect(self.update_monitor)
        port_layout.addWidget(self.port_combo)
        
        # Refresh port button
        self.refresh_button = QPushButton("⟳")
        self.refresh_button.setToolTip("Refresh Ports")
        self.refresh_button.setObjectName("iconButton")
        self.refresh_button.setFixedSize(
            self.scaler.value(30), 
            self.scaler.value(30)
        )
        self.refresh_button.clicked.connect(self.update_port_list)
        port_layout.addWidget(self.refresh_button)
        
        connection_layout.addLayout(port_layout)
        
        baud_layout = QHBoxLayout()
        baud_label = QLabel("BAUD")
        baud_label.setObjectName("sectionLabel")
        baud_layout.addWidget(baud_label)
        
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(['300', '1200', '2400', '4800', '9600', '19200', 
                                 '38400', '57600', '115200', '230400'])
        self.baud_combo.setCurrentText('9600')
        self.baud_combo.currentTextChanged.connect(self.update_monitor)
        baud_layout.addWidget(self.baud_combo)
        
        connection_layout.addLayout(baud_layout)
        
        # Connect button
        self.connect_button = QPushButton("CONNECT")
        self.connect_button.setObjectName("connectButton")
        self.connect_button.clicked.connect(self.toggle_connection)
        connection_layout.addWidget(self.connect_button)
        
        control_layout.addWidget(connection_group)
        
        # Sequence controls group
        sequence_panel = QWidget()
        sequence_panel.setObjectName("sequencePanel")
        sequence_layout = QVBoxLayout(sequence_panel)
        
        sequence_header = QLabel("COMMAND SEQUENCES")
        sequence_header.setObjectName("sectionLabel")
        sequence_layout.addWidget(sequence_header)
        
        sequence_combo_layout = QHBoxLayout()
        self.sequence_combo = QComboBox()
        self.update_sequence_combo()
        sequence_combo_layout.addWidget(self.sequence_combo, 1)
        
        self.run_sequence_button = QPushButton("▶ Run")
        self.run_sequence_button.setObjectName("actionButton")
        self.run_sequence_button.clicked.connect(self.run_selected_sequence)
        sequence_combo_layout.addWidget(self.run_sequence_button)
        
        sequence_layout.addLayout(sequence_combo_layout)
        
        sequence_buttons_layout = QHBoxLayout()
        self.save_sequence_button = QPushButton("Save New")
        self.save_sequence_button.clicked.connect(self.save_new_sequence)
        sequence_buttons_layout.addWidget(self.save_sequence_button)
        
        self.delete_sequence_button = QPushButton("Delete")
        self.delete_sequence_button.clicked.connect(self.delete_selected_sequence)
        sequence_buttons_layout.addWidget(self.delete_sequence_button)
        
        sequence_layout.addLayout(sequence_buttons_layout)
        
        control_layout.addWidget(sequence_panel)
        control_layout.setStretch(0, 1)
        control_layout.setStretch(1, 2)
        
        serial_layout.addWidget(control_panel)

        # RX Display with styled header
        rx_panel = QWidget()
        rx_panel.setObjectName("rxPanel")
        rx_layout = QVBoxLayout(rx_panel)
        
        rx_header = QWidget()
        rx_header.setObjectName("displayHeader")
        rx_header_layout = QHBoxLayout(rx_header)
        
        rx_title = QLabel("INCOMING TRANSMISSION")
        rx_title.setObjectName("displayTitle")
        rx_header_layout.addWidget(rx_title)
        rx_header_layout.addStretch()
        
        self.clear_rx_button = QPushButton("Clear")
        self.clear_rx_button.setObjectName("clearButton")
        self.clear_rx_button.clicked.connect(self.clear_rx_display)
        rx_header_layout.addWidget(self.clear_rx_button)
        
        rx_layout.addWidget(rx_header)
        
        self.rx_display = QTextEdit()
        self.rx_display.setReadOnly(True)
        self.rx_display.setObjectName("rxDisplay")
        rx_layout.addWidget(self.rx_display)
        
        serial_layout.addWidget(rx_panel, 10)  # More space for RX

        # TX Display with styled header
        tx_panel = QWidget()
        tx_panel.setObjectName("txPanel")
        tx_layout = QVBoxLayout(tx_panel)
        
        tx_header = QWidget()
        tx_header.setObjectName("displayHeader")
        tx_header_layout = QHBoxLayout(tx_header)
        
        tx_title = QLabel("OUTGOING TRANSMISSION")
        tx_title.setObjectName("displayTitle")
        tx_header_layout.addWidget(tx_title)
        tx_header_layout.addStretch()
        
        self.clear_tx_button = QPushButton("Clear")
        self.clear_tx_button.setObjectName("clearButton")
        self.clear_tx_button.clicked.connect(self.clear_tx_display)
        tx_header_layout.addWidget(self.clear_tx_button)
        
        tx_layout.addWidget(tx_header)
        
        self.tx_display = QTextEdit()
        self.tx_display.setReadOnly(True)
        self.tx_display.setObjectName("txDisplay")
        tx_layout.addWidget(self.tx_display)
        
        serial_layout.addWidget(tx_panel, 2)  # Less space for TX

        # Bottom control panel
        bottom_panel = QWidget()
        bottom_panel.setObjectName("bottomPanel")
        bottom_layout = QVBoxLayout(bottom_panel)
        
        # Input section
        input_panel = QWidget()
        input_panel.setObjectName("inputPanel")
        input_layout = QHBoxLayout(input_panel)
        self.scaler.margins(input_layout, 10, 10, 10, 10)
        
        self.input_line = QLineEdit()
        self.input_line.setObjectName("commandInput")
        self.input_line.setPlaceholderText("Type command here...")
        self.input_line.returnPressed.connect(self.send_data)
        input_layout.addWidget(self.input_line)
        
        bottom_layout.addWidget(input_panel)
        
        # Control buttons layout
        controls_panel = QWidget()
        controls_panel.setObjectName("controlsPanel")
        controls_layout = QHBoxLayout(controls_panel)
        
        # Special keys section
        keys_group = QWidget()
        keys_group.setObjectName("keysGroup")
        keys_layout = QHBoxLayout(keys_group)
        self.scaler.spacing(keys_layout, 8)
        
        self.transmit_button = QPushButton("⚡ TRANSMIT")
        self.transmit_button.setObjectName("transmitButton")
        self.transmit_button.clicked.connect(self.send_data)
        keys_layout.addWidget(self.transmit_button)
        
        keys_layout.addSpacing(self.scaler.value(20))
        
        keys_label = QLabel("SPECIAL KEYS:")
        keys_label.setObjectName("keysLabel")
        keys_layout.addWidget(keys_label)
        
        self.enter_key = QPushButton("ENTER")
        self.enter_key.setObjectName("specialKey")
        self.enter_key.clicked.connect(lambda: self.send_special_key("Enter"))
        keys_layout.addWidget(self.enter_key)
        
        self.esc_key = QPushButton("ESC")
        self.esc_key.setObjectName("specialKey")
        self.esc_key.clicked.connect(lambda: self.send_special_key("Escape"))
        keys_layout.addWidget(self.esc_key)
        
        self.backspace_key = QPushButton("⌫")
        self.backspace_key.setObjectName("specialKey")
        self.backspace_key.setToolTip("Backspace")
        self.backspace_key.clicked.connect(lambda: self.send_special_key("Backspace"))
        keys_layout.addWidget(self.backspace_key)
        
        self.tab_key = QPushButton("⇥")
        self.tab_key.setObjectName("specialKey")
        self.tab_key.setToolTip("Tab")
        self.tab_key.clicked.connect(lambda: self.send_special_key("Tab"))
        keys_layout.addWidget(self.tab_key)
        
        # Toggle switches section
        toggle_group = QWidget()
        toggle_group.setObjectName("toggleGroup")
        toggle_layout = QHBoxLayout(toggle_group)
        
        self.timestamp_toggle = QPushButton("TIMECODE")
        self.timestamp_toggle.setObjectName("toggleButton")
        self.timestamp_toggle.setCheckable(True)
        self.timestamp_toggle.clicked.connect(self.toggle_timestamp)
        toggle_layout.addWidget(self.timestamp_toggle)
        
        self.hex_toggle = QPushButton("HEX MODE")
        self.hex_toggle.setObjectName("toggleButton")
        self.hex_toggle.setCheckable(True)
        self.hex_toggle.clicked.connect(self.toggle_hex)
        toggle_layout.addWidget(self.hex_toggle)
        
        self.raw_mode_toggle = QPushButton("AUTO-TERM")
        self.raw_mode_toggle.setObjectName("toggleButton")
        self.raw_mode_toggle.setCheckable(True)
        self.raw_mode_toggle.setChecked(True)
        self.raw_mode_toggle.clicked.connect(self.toggle_raw_mode)
        toggle_layout.addWidget(self.raw_mode_toggle)
        
        self.auto_clear_toggle = QPushButton("AUTO-CLEAR")
        self.auto_clear_toggle.setObjectName("toggleButton")
        self.auto_clear_toggle.setCheckable(True)
        self.auto_clear_toggle.setChecked(self.auto_clear_rx)
        self.auto_clear_toggle.clicked.connect(self.toggle_auto_clear)
        toggle_layout.addWidget(self.auto_clear_toggle)
        
        self.clear_all_button = QPushButton("CLEAR ALL")
        self.clear_all_button.setObjectName("clearAllButton")
        self.clear_all_button.clicked.connect(self.clear_all_displays)
        toggle_layout.addWidget(self.clear_all_button)
        
        controls_layout.addWidget(keys_group, 3)
        controls_layout.addWidget(toggle_group, 2)
        
        bottom_layout.addWidget(controls_panel)
        
        serial_layout.addWidget(bottom_panel, 1)
    
    def setup_fonts(self):
        """Set up fonts with proper scaling."""
        # Define font stacks
        code_font = "JetBrains Mono, Fira Code, Source Code Pro, Consolas, Courier New"
        ui_font = "Segoe UI, Roboto, Arial, sans-serif"
        
        # Create and configure a monospace font with scaled size
        monospace_font = QFont()
        monospace_font.setFamily("JetBrains Mono")
        monospace_font.setPointSize(self.scaler.value(14))
        monospace_font.setStyleHint(QFont.StyleHint.Monospace)
        
        # Apply to text elements
        self.rx_display.setFont(monospace_font)
        self.tx_display.setFont(monospace_font)
        self.input_line.setFont(monospace_font)
    
    def update_port_list(self):
        """Update the list of available serial ports."""
        import serial.tools.list_ports
        
        current_port = self.port_combo.currentText()
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)
        
        # Restore previous selection if it still exists
        index = self.port_combo.findText(current_port)
        if index >= 0:
            self.port_combo.setCurrentIndex(index)
        
        self.status_message.emit(f"Found {len(ports)} serial ports", 0)
        
    def update_monitor(self):
        """Update serial monitor settings based on current UI selections."""
        if self.monitor:
            self.monitor.stop()
            if self.serial_thread:
                self.serial_thread.quit()
                self.serial_thread.wait()
        
        port = self.port_combo.currentText()
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
            self.setup_serial_thread()
            self.update_status()
    
    def toggle_connection(self):
        """Toggle serial connection state."""
        if not self.monitor:
            self.update_monitor()
        
        if self.monitor and self.monitor.ser and self.monitor.ser.is_open:
            self.monitor.stop()
            self.connect_button.setText("CONNECT")
            self.connect_button.setChecked(False)
        else:
            if self.monitor and self.monitor.start():
                self.connect_button.setText("DISCONNECT")
                self.connect_button.setChecked(True)
        self.update_status()
    
    def setup_serial_thread(self):
        """Set up the thread for asynchronous serial operations."""
        self.serial_thread = SerialThread(self.monitor)
        self.serial_thread.data_received.connect(self.update_rx_display)
        self.serial_thread.error_occurred.connect(self.handle_error)
        self.serial_thread.start()
    
    def update_rx_display(self, text):
        """Update the RX display with received data."""
        if self.monitor.hex_display:
            text = ' '.join(f'{ord(c):02X}' for c in text)
        if self.monitor.timestamp:
            text = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {text}"

        cursor = self.rx_display.textCursor()
        format = QTextCharFormat()
        format.setForeground(QColor("#7EC7A2"))  # Green for RX
        cursor.setCharFormat(format)
        cursor.insertText(f"[RX] {text}\n")
        self.rx_display.setTextCursor(cursor)
        self.rx_display.ensureCursorVisible()
    
    def send_data(self):
        """Send data to the serial port."""
        if not self.monitor or not self.monitor.ser or not self.monitor.ser.is_open:
            self.handle_error("Not connected")
            return
            
        # Clear RX display if auto-clear is enabled
        if self.auto_clear_rx:
            self.clear_rx_display()
            
        text = self.input_line.text().strip()
        if text:
            sent_data = self.monitor.send_data(text)
            if sent_data:
                display_text = text
                if self.monitor.hex_display:
                    display_text = ' '.join(f'{b:02X}' for b in sent_data)
                if self.monitor.timestamp:
                    display_text = f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {display_text}"

                cursor = self.tx_display.textCursor()
                format = QTextCharFormat()
                format.setForeground(QColor("#61afef"))  # Blue for TX
                cursor.setCharFormat(format)
                cursor.insertText(f"[TX] {display_text}\n")
                self.tx_display.setTextCursor(cursor)
                self.tx_display.ensureCursorVisible()
            self.input_line.clear()
    
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
            # Display the key press in the TX display
            cursor = self.tx_display.textCursor()
            format = QTextCharFormat()
            format.setForeground(QColor("#61afef"))  # Blue for TX
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
            else:
                self.timestamp_toggle.setChecked(False)
    
    def toggle_hex(self):
        """Toggle hex display mode."""
        if self.monitor:
            self.monitor.hex_display = not self.monitor.hex_display
            if self.monitor.hex_display:
                self.hex_toggle.setChecked(True)
            else:
                self.hex_toggle.setChecked(False)
    
    def toggle_raw_mode(self):
        """Toggle raw mode (whether termination chars are auto-added)."""
        if self.monitor:
            self.monitor.auto_termination = not self.monitor.auto_termination
            if self.monitor.auto_termination:
                self.raw_mode_toggle.setChecked(True)
            else:
                self.raw_mode_toggle.setChecked(False)
                
            # Update status to show the change
            mode_text = "with auto termination" if self.monitor.auto_termination else "in raw mode"
            self.status_message.emit(f"Serial now operating {mode_text}", 0)
    
    def toggle_auto_clear(self):
        """Toggle auto-clear of RX display on new command."""
        self.auto_clear_rx = not self.auto_clear_rx
        if self.auto_clear_rx:
            self.auto_clear_toggle.setChecked(True)
            self.status_message.emit("Auto-clear RX on command: ENABLED", 0)
        else:
            self.auto_clear_toggle.setChecked(False)
            self.status_message.emit("Auto-clear RX on command: DISABLED", 0)
    
    def clear_rx_display(self):
        """Clear the RX display window."""
        self.rx_display.clear()
        self.status_message.emit("RX display cleared", 0)
    
    def clear_tx_display(self):
        """Clear the TX display window."""
        self.tx_display.clear()
        self.status_message.emit("TX display cleared", 0)
    
    def clear_all_displays(self):
        """Clear both RX and TX display windows."""
        self.rx_display.clear()
        self.tx_display.clear()
        self.status_message.emit("All displays cleared", 0)
    
    def update_status(self):
        """Update connection status in parent window."""
        # Emit status to parent window
        port = self.port_combo.currentText() or "N/A"
        baud = self.baud_combo.currentText()
        status = "ONLINE" if self.monitor and self.monitor.ser and self.monitor.ser.is_open else "OFFLINE"
        
        # Update button appearance based on connection status
        if status == "ONLINE":
            self.connect_button.setText("DISCONNECT")
            self.connect_button.setChecked(True)
        else:
            self.connect_button.setText("CONNECT")
            self.connect_button.setChecked(False)
        
        # Emit connection info to parent
        self.status_message.emit(f"PORT: {port} | BAUD: {baud} | STATUS: {status}", 0)
    
    def handle_error(self, message):
        """Handle error messages and update UI."""
        self.error_occurred.emit(message)
        
        # Make errors more visible in RX display
        cursor = self.rx_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        format = QTextCharFormat()
        format.setForeground(QColor("#e06c75"))  # Red for errors
        cursor.setCharFormat(format)
        cursor.insertText(f"[ERROR] {message}\n")
        self.rx_display.setTextCursor(cursor)
        self.rx_display.ensureCursorVisible()
    
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
            self.status_message.emit(f"Saved sequence: {name}", 0)
    
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
                self.status_message.emit(f"Deleted sequence: {name}", 0)
    
    def run_selected_sequence(self):
        """Run the currently selected command sequence."""
        name = self.sequence_combo.currentText()
        if name and name != "-- Select Sequence --" and name in self.command_sequences:
            # Reset sequence
            sequence = self.command_sequences[name]
            sequence.reset()
            
            # Store as current sequence
            self.current_sequence = sequence
            
            # Start execution
            self.execute_next_sequence_step()
    
    def execute_next_sequence_step(self):
        """Execute the next step in the current sequence."""
        if not self.current_sequence:
            return
            
        # Get next command
        cmd_info = self.current_sequence.get_next_command()
        if not cmd_info:
            self.status_message.emit(f"Sequence '{self.current_sequence.name}' completed", 0)
            self.current_sequence = None
            return
        
        # Send the command
        command = cmd_info['command']
        
        # Show what we're doing
        self.status_message.emit(f"Sending: {command}", 0)
        
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