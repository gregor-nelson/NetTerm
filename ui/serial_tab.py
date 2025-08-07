"""
Enhanced Serial Monitor tab UI component with ribbon-style layout.
Follows Windows system application design patterns.
"""
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                           QLineEdit, QPushButton, QLabel, QComboBox, 
                           QInputDialog, QMessageBox, QGroupBox, QSplitter,
                           QFrame, QCompleter, QToolButton, QStyle, QSpacerItem,
                           QSizePolicy, QCheckBox, QGridLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QFont, QIcon

from core.serial_monitor import SerialMonitor
from core.serial_thread import SerialThread
from utils.icon_helper import (get_connect_icon, get_refresh_icon, get_enter_icon, 
                             get_escape_icon, get_toggle_icon, get_clear_icon,
                             get_timestamp_icon, get_hex_icon, get_auto_term_icon,
                             get_filter_icon, get_auto_clear_icon, get_clear_all_icon,
                             get_send_icon, get_history_icon)


class SerialTab(QWidget):
    """Enhanced Serial Monitor tab UI component with ribbon-style layout."""
    
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
        
        # Initialize stats
        self.rx_bytes = 0
        self.tx_bytes = 0
        self.last_rx = 0
        self.last_tx = 0
        self.last_time = datetime.now()
        
        # Store command history
        self.command_history = []
        self.history_index = -1
        
        # Setup UI
        self.init_ui()
        self.setup_fonts()
        self.setup_command_completer()
        self.update_port_list()
        
        # Create timer for stats update
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)  # Update every second
    
    def init_ui(self):
        """Initialize the Enhanced Serial Monitor tab UI with ribbon layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create ribbon toolbar
        ribbon_widget = self.create_ribbon_widget()
        main_layout.addWidget(ribbon_widget)
        
        # Create content area with TX/RX displays
        content_widget = self.create_content_area()
        main_layout.addWidget(content_widget, 1)
        
        # Create command bar
        command_bar = self.create_command_bar()
        main_layout.addWidget(command_bar)
        
        # Create enhanced status bar
        status_bar = self.create_status_bar()
        main_layout.addWidget(status_bar)
    
    def create_ribbon_widget(self):
        """Create the ribbon-style toolbar with sections."""
        ribbon_container = QWidget()
        ribbon_container.setMaximumHeight(self.scaler.value(90))
        
        # Create frame for the ribbon with subtle border
        ribbon_frame = QFrame(ribbon_container)
        ribbon_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        ribbon_frame.setLineWidth(1)
        
        # Main ribbon layout
        container_layout = QVBoxLayout(ribbon_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(ribbon_frame)
        
        ribbon_layout = QHBoxLayout(ribbon_frame)
        self.scaler.margins(ribbon_layout, 12, 8, 12, 8)
        self.scaler.spacing(ribbon_layout, 16)
        
        # Add sections
        ribbon_layout.addLayout(self.create_connection_section())
        ribbon_layout.addWidget(self.create_separator())
        ribbon_layout.addLayout(self.create_format_section())
        ribbon_layout.addWidget(self.create_separator())
        ribbon_layout.addLayout(self.create_view_section())
        ribbon_layout.addStretch()
        
        return ribbon_container
    
    def create_connection_section(self):
        """Create the connection section of the ribbon."""
        section_layout = QVBoxLayout()
        section_layout.setSpacing(self.scaler.value(8))
        
        # Section header
        header = self.create_section_header("Connection")
        section_layout.addWidget(header)
        
        # Controls layout
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(self.scaler.value(8))
        
        # Row 1: Port selection and Baud rate
        row1 = QHBoxLayout()
        row1.setSpacing(self.scaler.value(8))
        
        # Port selection with minimum width
        self.port_combo = QComboBox()
        self.port_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.port_combo.setMinimumWidth(self.scaler.value(200))
        self.port_combo.currentTextChanged.connect(self.update_monitor)
        row1.addWidget(self.port_combo)
        
        # Baud rate with fixed width
        self.baud_combo = QComboBox()
        self.baud_combo.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.baud_combo.setFixedWidth(self.scaler.value(100))
        self.baud_combo.addItems(['300', '1200', '2400', '4800', '9600', '19200', 
                                 '38400', '57600', '115200', '230400'])
        self.baud_combo.setCurrentText('9600')
        self.baud_combo.currentTextChanged.connect(self.update_monitor)
        row1.addWidget(self.baud_combo)
        
        controls_layout.addLayout(row1)
        
        # Row 2: Refresh and Connect buttons
        row2 = QHBoxLayout()
        row2.setSpacing(self.scaler.value(8))
        
        # Refresh button (text and icon)
        self.refresh_button = QToolButton()
        self.refresh_button.setText("Refresh")
        self.refresh_button.setIcon(get_refresh_icon())
        self.refresh_button.setToolTip("Refresh Ports")
        self.refresh_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.refresh_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.refresh_button.clicked.connect(self.update_port_list)
        row2.addWidget(self.refresh_button)
        
        # Connect button - primary action
        self.connect_button = QToolButton()
        self.connect_button.setText("Connect")
        self.connect_button.setIcon(get_connect_icon())
        self.connect_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.connect_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.connect_button.setCheckable(True)
        self.connect_button.clicked.connect(self.toggle_connection)
        row2.addWidget(self.connect_button)
        
        # Add stretch to left-align buttons
        row2.addStretch()
        
        controls_layout.addLayout(row2)
        
        section_layout.addLayout(controls_layout)
        section_layout.addStretch()
        
        return section_layout
    
    def create_format_section(self):
        """Create the data format section of the ribbon."""
        section_layout = QVBoxLayout()
        section_layout.setSpacing(self.scaler.value(8))
        
        # Section header
        header = self.create_section_header("Data Format")
        section_layout.addWidget(header)
        
        # Grid layout for toggle buttons (2x2)
        grid = QGridLayout()
        grid.setSpacing(self.scaler.value(8))
        grid.setHorizontalSpacing(self.scaler.value(8))
        grid.setVerticalSpacing(self.scaler.value(8))
        
        # Create toggle buttons with consistent styling
        self.timestamp_check = self.create_toggle_button("Timestamp", "Add timestamps to data", 
                                                       checked=False, icon_checked=get_timestamp_icon(),
                                                       icon_unchecked=get_toggle_icon(False))
        self.timestamp_check.clicked.connect(self.toggle_timestamp)
        grid.addWidget(self.timestamp_check, 0, 0)
        
        self.hex_check = self.create_toggle_button("Hex Mode", "Display data as hexadecimal", 
                                                 checked=False, icon_checked=get_hex_icon(),
                                                 icon_unchecked=get_toggle_icon(False))
        self.hex_check.clicked.connect(self.toggle_hex)
        grid.addWidget(self.hex_check, 0, 1)
        
        self.auto_term_check = self.create_toggle_button("Auto-Term", "Automatically add line terminators", 
                                                       checked=True, icon_checked=get_auto_term_icon(),
                                                       icon_unchecked=get_toggle_icon(False))
        self.auto_term_check.clicked.connect(self.toggle_raw_mode)
        grid.addWidget(self.auto_term_check, 1, 0)
        
        section_layout.addLayout(grid)
        section_layout.addStretch()
        
        return section_layout
    
    def create_view_section(self):
        """Create the view section of the ribbon."""
        section_layout = QVBoxLayout()
        section_layout.setSpacing(self.scaler.value(8))
        
        # Section header
        header = self.create_section_header("View")
        section_layout.addWidget(header)
        
        # Controls layout
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(self.scaler.value(8))
        
        # Row 1: Filter and Auto-Clear toggle buttons
        row1 = QHBoxLayout()
        row1.setSpacing(self.scaler.value(8))
        
        self.filter_check = self.create_toggle_button("Filter RX", 
            "Filter Incoming Data\n\n"
            "• Shows printable characters\n"
            "• Preserves newlines and tabs\n"
            "• Shows non-printable as [XX]",
            checked=False, icon_checked=get_filter_icon(),
            icon_unchecked=get_toggle_icon(False))
        self.filter_check.clicked.connect(self.toggle_rx_filter)
        row1.addWidget(self.filter_check)
        
        self.auto_clear_check = self.create_toggle_button("Auto-Clear", "Clear RX display when sending new command",
                                                        checked=self.auto_clear_rx, icon_checked=get_auto_clear_icon(),
                                                        icon_unchecked=get_toggle_icon(False))
        self.auto_clear_check.clicked.connect(self.toggle_auto_clear)
        row1.addWidget(self.auto_clear_check)
        
        # Add stretch to left-align buttons
        row1.addStretch()
        
        controls_layout.addLayout(row1)
        
        # Row 2: Clear All button
        self.clear_all_button = QToolButton()
        self.clear_all_button.setText("Clear All")
        self.clear_all_button.setIcon(get_clear_all_icon())
        self.clear_all_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.clear_all_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.clear_all_button.clicked.connect(self.clear_all_displays)
        controls_layout.addWidget(self.clear_all_button)
        
        section_layout.addLayout(controls_layout)
        section_layout.addStretch()
        
        return section_layout
    
    def create_command_bar(self):
        """Create the unified command bar."""
        command_container = QWidget()
        command_container.setMaximumHeight(self.scaler.value(48))
        
        # Frame for the command bar (no border)
        command_frame = QFrame(command_container)
        
        container_layout = QVBoxLayout(command_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(command_frame)
        
        # Main command bar layout
        command_layout = QHBoxLayout(command_frame)
        self.scaler.margins(command_layout, 12, 6, 12, 6)
        self.scaler.spacing(command_layout, 8)
        
        # Command input - takes most space
        self.input_line = QLineEdit()
        self.input_line.setFont(self.scaler.get_code_font())
        self.input_line.setPlaceholderText("Type command here...")
        self.input_line.setClearButtonEnabled(True)
        self.input_line.setMinimumWidth(self.scaler.value(300))
        self.input_line.setMinimumHeight(self.scaler.value(28))
        self.input_line.returnPressed.connect(self.send_data)
        self.input_line.installEventFilter(self)
        command_layout.addWidget(self.input_line, 3)  # Stretch factor 3
        
        # Primary Send button
        self.send_button = QToolButton()
        self.send_button.setText("Send")
        self.send_button.setIcon(get_send_icon())
        self.send_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.send_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.send_button.clicked.connect(self.send_data)
        command_layout.addWidget(self.send_button)
        
        # Separator
        command_layout.addWidget(self.create_separator())
        
        # Special keys section
        self.enter_key = QToolButton()
        self.enter_key.setText("Enter")
        self.enter_key.setIcon(get_enter_icon())
        self.enter_key.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.enter_key.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.enter_key.clicked.connect(lambda: self.send_special_key("Enter"))
        command_layout.addWidget(self.enter_key)
        
        self.esc_key = QToolButton()
        self.esc_key.setText("Esc")
        self.esc_key.setIcon(get_escape_icon())
        self.esc_key.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.esc_key.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.esc_key.clicked.connect(lambda: self.send_special_key("Escape"))
        command_layout.addWidget(self.esc_key)
        
        # Separator
        command_layout.addWidget(self.create_separator())
        
        # History button
        self.history_button = QToolButton()
        self.history_button.setText("History")
        self.history_button.setIcon(get_history_icon())
        self.history_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.history_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        self.history_button.setToolTip("Command History (Ctrl+H)")
        self.history_button.clicked.connect(self.show_command_history)
        command_layout.addWidget(self.history_button)
        
        # Push everything to the left
        command_layout.addStretch()
        
        return command_container
    
    def create_content_area(self):
        """Create the content area with TX/RX displays."""
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        self.scaler.margins(content_layout, 12, 8, 12, 8)
        content_layout.setSpacing(0)
        
        # Create splitter for TX/RX displays
        display_splitter = QSplitter(Qt.Orientation.Horizontal)
        display_splitter.setChildrenCollapsible(False)
        
        # TX Display panel
        tx_panel = self.create_display_panel("Transmitted Data (TX)", is_tx=True)
        display_splitter.addWidget(tx_panel)
        
        # RX Display panel
        rx_panel = self.create_display_panel("Received Data (RX)", is_tx=False)
        display_splitter.addWidget(rx_panel)
        
        # Set initial sizes - equal
        display_splitter.setSizes([self.scaler.value(500), self.scaler.value(500)])
        
        content_layout.addWidget(display_splitter)
        
        return content_widget
    
    def create_display_panel(self, title, is_tx=True):
        """Create a TX or RX display panel with integrated header."""
        panel = QFrame()
        
        panel_layout = QVBoxLayout(panel)
        self.scaler.margins(panel_layout, 8, 8, 8, 8)
        panel_layout.setSpacing(4)
        
        # Create header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 4)
        
        # Title
        title_label = QLabel(title)
        title_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
        header_layout.addWidget(title_label)
        
        # Byte count (will be updated dynamically)
        if is_tx:
            self.tx_byte_label = QLabel("0 bytes")
            self.tx_byte_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
            palette = self.tx_byte_label.palette()
            self.tx_byte_label.setForegroundRole(palette.ColorRole.PlaceholderText)
            header_layout.addWidget(self.tx_byte_label)
        else:
            self.rx_byte_label = QLabel("0 bytes")
            self.rx_byte_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
            palette = self.rx_byte_label.palette()
            self.rx_byte_label.setForegroundRole(palette.ColorRole.PlaceholderText)
            header_layout.addWidget(self.rx_byte_label)
        
        header_layout.addStretch()
        
        # Clear button (flat style)
        clear_button = QToolButton()
        clear_button.setText("Clear")
        clear_button.setIcon(get_clear_icon())
        clear_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        clear_button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        clear_button.setAutoRaise(True)  # Flat appearance until hovered
        
        if is_tx:
            clear_button.clicked.connect(self.clear_tx_display)
            self.clear_tx_button = clear_button
        else:
            clear_button.clicked.connect(self.clear_rx_display)
            self.clear_rx_button = clear_button
        
        header_layout.addWidget(clear_button)
        
        panel_layout.addWidget(header_widget)
        
        # Create text display
        display = QTextEdit()
        display.setReadOnly(True)
        display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        display.setFont(self.scaler.get_code_font())
        
        if is_tx:
            self.tx_display = display
        else:
            self.rx_display = display
        
        panel_layout.addWidget(display)
        
        return panel
    
    def create_status_bar(self):
        """Create the enhanced status bar."""
        status_container = QFrame()
        status_container.setMaximumHeight(self.scaler.value(32))
        
        status_layout = QHBoxLayout(status_container)
        self.scaler.margins(status_layout, 12, 4, 12, 4)
        self.scaler.spacing(status_layout, 16)
        
        # Connection status with indicator
        connection_widget = QWidget()
        connection_layout = QHBoxLayout(connection_widget)
        connection_layout.setContentsMargins(0, 0, 0, 0)
        connection_layout.setSpacing(4)
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_MEDIUM))
        self.update_status_indicator("disconnected")
        connection_layout.addWidget(self.status_indicator)
        
        self.connection_label = QLabel("Disconnected")
        self.connection_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        connection_layout.addWidget(self.connection_label)
        
        status_layout.addWidget(connection_widget)
        
        # Separator
        status_layout.addWidget(self.create_separator())
        
        # Port info
        self.port_info_label = QLabel("No Port Selected")
        self.port_info_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        status_layout.addWidget(self.port_info_label)
        
        # Separator
        status_layout.addWidget(self.create_separator())
        
        # RX Statistics
        self.rx_stats_label = QLabel("RX: 0 B/s")
        self.rx_stats_label.setFont(self.scaler.get_code_font(self.scaler.FONT_SIZE_SMALL))
        status_layout.addWidget(self.rx_stats_label)
        
        # TX Statistics
        self.tx_stats_label = QLabel("TX: 0 B/s")
        self.tx_stats_label.setFont(self.scaler.get_code_font(self.scaler.FONT_SIZE_SMALL))
        status_layout.addWidget(self.tx_stats_label)
        
        # Separator
        status_layout.addWidget(self.create_separator())
        
        # Line count
        self.line_count_label = QLabel("Lines: 0")
        self.line_count_label.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        status_layout.addWidget(self.line_count_label)
        
        # Push everything to the left
        status_layout.addStretch()
        
        return status_container
    
    def create_section_header(self, text):
        """Create a section header label."""
        label = QLabel(text)
        font = self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL)
        font.setBold(True)
        label.setFont(font)
        return label
    
    def create_separator(self):
        """Create a vertical separator."""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setLineWidth(1)
        return separator
    
    def create_toggle_button(self, text, tooltip=None, checked=False, icon_checked=None, icon_unchecked=None):
        """Create a standardized toggle button with consistent styling."""
        button = QToolButton()
        button.setText(text)
        button.setCheckable(True)
        button.setChecked(checked)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setFont(self.scaler.get_ui_font(self.scaler.FONT_SIZE_SMALL))
        
        # Set tooltip if provided
        if tooltip:
            button.setToolTip(tooltip)
        
        # Set default icons if none provided
        if not icon_checked:
            icon_checked = get_toggle_icon(True)
        if not icon_unchecked:
            icon_unchecked = get_toggle_icon(False)
        
        # Update icon based on checked state
        def update_icon():
            if button.isChecked():
                button.setIcon(icon_checked)
            else:
                button.setIcon(icon_unchecked)
        
        # Set initial icon and connect toggle handler
        update_icon()
        button.toggled.connect(lambda: update_icon())
        
        return button
    
    def update_status_indicator(self, state):
        """Update the status indicator color based on state."""
        palette = self.status_indicator.palette()
        if state == "connected":
            # Green for connected
            palette.setColor(palette.ColorRole.WindowText, Qt.GlobalColor.green)
        elif state == "connecting":
            # Yellow for connecting
            palette.setColor(palette.ColorRole.WindowText, Qt.GlobalColor.yellow)
        elif state == "error":
            # Red for error
            palette.setColor(palette.ColorRole.WindowText, Qt.GlobalColor.red)
        else:
            # Gray for disconnected
            palette.setColor(palette.ColorRole.WindowText, 
                           palette.color(palette.ColorGroup.Disabled, palette.ColorRole.WindowText))
        self.status_indicator.setPalette(palette)
    
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
        
        current_port = self.port_combo.currentData()
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
            auto_term = self.auto_term_check.isChecked() if hasattr(self, 'auto_term_check') else True
                
            self.monitor = SerialMonitor(
                port=port, 
                baudrate=baudrate, 
                timestamp=self.timestamp_check.isChecked() if hasattr(self, 'timestamp_check') else False,
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
            self.connect_button.setIcon(get_connect_icon())
            self.connect_button.setChecked(False)
            self.connection_label.setText("Disconnected")
            self.update_status_indicator("disconnected")
        else:
            if self.monitor and self.monitor.start():
                self.connect_button.setText("Disconnect")
                self.connect_button.setIcon(get_clear_icon())
                self.connect_button.setChecked(True)
                self.connection_label.setText("Connected")
                self.update_status_indicator("connected")
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
        
        # Update byte label
        self.rx_byte_label.setText(f"{self.rx_bytes} bytes")
        
        # Apply filtering if enabled
        if hasattr(self, 'filter_check') and self.filter_check.isChecked():
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
        
        # Update line count
        self.update_line_count()
    
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
            
            # Enhanced visual feedback
            self.input_line.setEnabled(False)
            self.send_button.setText("Sending...")
            self.send_button.setIcon(get_toggle_icon(True))
            
            # Use a timer to restore the UI after a short delay
            QTimer.singleShot(200, self.restore_send_ui)
            
            # Continue with data sending
            sent_data = self.monitor.send_data(text)
            if sent_data:
                # Update byte count for statistics
                self.tx_bytes += len(sent_data)
                if hasattr(self.monitor, 'stats'):
                    self.monitor.stats['tx_bytes'] = self.tx_bytes
                
                # Update byte label
                self.tx_byte_label.setText(f"{self.tx_bytes} bytes")
                
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
                
                # Update line count
                self.update_line_count()
            self.input_line.clear()
    
    def restore_send_ui(self):
        """Restore UI after send operation with enhanced feedback."""
        self.input_line.setEnabled(True)
        self.input_line.setFocus()
        self.send_button.setText("Send")
        self.send_button.setIcon(get_send_icon())
    
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
            
            # Update byte label
            self.tx_byte_label.setText(f"{self.tx_bytes} bytes")
            
            # Display the key press in the TX display
            cursor = self.tx_display.textCursor()
            format = QTextCharFormat()
            cursor.setCharFormat(format)
            cursor.insertText(f"[KEY] {key}\n")
            self.tx_display.setTextCursor(cursor)
            self.tx_display.ensureCursorVisible()
            
            # Update line count
            self.update_line_count()
    
    def toggle_timestamp(self):
        """Toggle timestamp display."""
        if self.monitor:
            self.monitor.timestamp = self.timestamp_check.isChecked()
            self.status_message.emit(f"Timestamp: {'ON' if self.monitor.timestamp else 'OFF'}", 3000)
    
    def toggle_hex(self):
        """Toggle hex display mode."""
        if self.monitor:
            self.monitor.hex_display = self.hex_check.isChecked()
            self.status_message.emit(f"Hex mode: {'ON' if self.monitor.hex_display else 'OFF'}", 3000)
    
    def toggle_raw_mode(self):
        """Toggle raw mode (whether termination chars are auto-added)."""
        if self.monitor:
            self.monitor.auto_termination = self.auto_term_check.isChecked()
            self.status_message.emit(f"Auto-termination: {'ON' if self.monitor.auto_termination else 'OFF (Raw Mode)'}", 3000)
    
    def toggle_auto_clear(self):
        """Toggle auto-clear of RX display on new command."""
        self.auto_clear_rx = self.auto_clear_check.isChecked()
        self.status_message.emit(f"Auto-clear: {'ON' if self.auto_clear_rx else 'OFF'}", 3000)
    
    def toggle_rx_filter(self):
        """Toggle filtering of non-printable characters in RX display."""
        self.status_message.emit(f"RX filter: {'ON' if self.filter_check.isChecked() else 'OFF'}", 3000)
    
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
        """Update connection status in status bar."""
        port = self.port_combo.currentData() or "None"
        baud = self.baud_combo.currentText()
        
        if self.monitor and self.monitor.ser and self.monitor.ser.is_open:
            self.port_info_label.setText(f"{port} @ {baud} 8N1")
            self.connection_label.setText("Connected")
            self.update_status_indicator("connected")
        else:
            self.port_info_label.setText("No Connection")
            self.connection_label.setText("Disconnected")
            self.update_status_indicator("disconnected")
    
    def handle_error(self, message):
        """Handle error messages and update UI."""
        self.error_occurred.emit(message)
        
        # Update status indicator
        self.update_status_indicator("error")
        
        # Make errors more visible in RX display
        cursor = self.rx_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        format = QTextCharFormat()
        cursor.setCharFormat(format)
        cursor.insertText(f"[ERROR] {message}\n")
        self.rx_display.setTextCursor(cursor)
        self.rx_display.ensureCursorVisible()
        
        # Update line count
        self.update_line_count()
        
        # Provide visual feedback
        QTimer.singleShot(100, lambda: self.flash_error_indicator(message))
    
    def flash_error_indicator(self, message):
        """Flash an error message in the status bar."""
        self.status_message.emit(f"ERROR: {message}", 5000)
        
        # Restore UI if needed
        if not self.input_line.isEnabled():
            self.restore_send_ui()
        
        # Restore normal status indicator after delay
        QTimer.singleShot(3000, lambda: self.update_status_indicator("disconnected"))
    
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
                rx_rate_str = f"RX: {rx_rate:.1f} B/s"
            else:
                rx_rate_str = f"RX: {rx_rate/1024:.1f} KB/s"
                
            if tx_rate < 1024:
                tx_rate_str = f"TX: {tx_rate:.1f} B/s"
            else:
                tx_rate_str = f"TX: {tx_rate/1024:.1f} KB/s"
            
            # Update labels
            self.rx_stats_label.setText(rx_rate_str)
            self.tx_stats_label.setText(tx_rate_str)
            
            # Store values for next calculation
            self.last_rx = self.rx_bytes
            self.last_tx = self.tx_bytes
            self.last_time = now
    
    def update_line_count(self):
        """Update the line count in the status bar."""
        rx_lines = self.rx_display.document().lineCount()
        tx_lines = self.tx_display.document().lineCount()
        total_lines = rx_lines + tx_lines
        self.line_count_label.setText(f"Lines: {total_lines:,}")
