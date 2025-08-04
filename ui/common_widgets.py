"""
Common reusable UI widgets for the Network Tools application.
These widgets maintain consistent styling and behavior across the application.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QPushButton, QLineEdit, QLabel, QGroupBox, 
                           QVBoxLayout, QHBoxLayout, QDialog, QMessageBox,
                           QTextEdit, QFileDialog, QComboBox, QWidget,
                           QProgressBar)
from PyQt6.QtGui import QIcon, QFont, QTextCursor, QTextCharFormat


class StyledButton(QPushButton):
    """Button with consistent styling and optional icon support."""
    
    def __init__(self, text, scaler, icon=None, accent=False, destructive=False, parent=None):
        """
        Initialize a styled button.
        
        Args:
            text: Button text
            scaler: UIScaler instance for consistent sizing
            icon: Optional icon name (without extension)
            accent: Whether this is an accent (primary) button
            destructive: Whether this is a destructive action button
            parent: Parent widget
        """
        super().__init__(text, parent)
        
        # Apply consistent font and sizing
        if accent:
            self.setFont(scaler.get_ui_font(scaler.FONT_SIZE_MEDIUM, weight=QFont.Weight.Bold))
            self.setMinimumHeight(scaler.value(36))
        else:
            self.setFont(scaler.get_ui_font(scaler.FONT_SIZE_MEDIUM))
            self.setMinimumHeight(scaler.value(32))
        
        if icon:
            self.setIcon(QIcon(f"icons/{icon}.png"))


class LabeledInput(QGroupBox):
    """Input field with a label for form layouts."""
    
    def __init__(self, label_text, scaler, placeholder="", parent=None):
        """
        Initialize a labeled input.
        
        Args:
            label_text: Label text
            scaler: UIScaler instance for consistent sizing
            placeholder: Input placeholder text
            parent: Parent widget
        """
        super().__init__(parent)
        self.setTitle("")  # No title for the group box
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        scaler.spacing(layout, scaler.SPACING_SMALL)
        
        self.label = QLabel(label_text)
        self.label.setFont(scaler.get_ui_font(scaler.FONT_SIZE_SMALL))
        
        self.input = QLineEdit()
        self.input.setFont(scaler.get_ui_font(scaler.FONT_SIZE_MEDIUM))
        self.input.setMinimumHeight(scaler.value(28))
        self.input.setPlaceholderText(placeholder)
        
        layout.addWidget(self.label)
        layout.addWidget(self.input)
    
    def text(self):
        """Get the input text."""
        return self.input.text()
    
    def setText(self, text):
        """Set the input text."""
        self.input.setText(text)


class StatusIndicator(QLabel):
    """Status indicator with colored text based on status."""
    
    def __init__(self, scaler, parent=None):
        """
        Initialize a status indicator.
        
        Args:
            scaler: UIScaler instance for consistent sizing
            parent: Parent widget
        """
        super().__init__(parent)
        self.setFont(scaler.get_ui_font(scaler.FONT_SIZE_MEDIUM))
        self.setStatus("default", "Status")
    
    def setStatus(self, status_type, text):
        """
        Set the status with appropriate color.
        
        Args:
            status_type: Status type (online, offline, warning, default)
            text: Status text
        """
        # Use default styling from Fusion theme
        self.setText(text)


class ProgressDialog(QDialog):
    """Dialog showing progress with cancel option."""
    
    canceled = pyqtSignal()
    
    def __init__(self, title, message, scaler, parent=None):
        """
        Initialize a progress dialog.
        
        Args:
            title: Dialog title
            message: Progress message
            scaler: UIScaler instance for consistent sizing
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(scaler.value(400))
        
        layout = QVBoxLayout(self)
        scaler.spacing(layout, scaler.SPACING_MEDIUM)
        scaler.margins(layout, scaler.SPACING_LARGE, scaler.SPACING_LARGE, scaler.SPACING_LARGE, scaler.SPACING_LARGE)
        
        self.message_label = QLabel(message)
        self.message_label.setFont(scaler.get_ui_font(scaler.FONT_SIZE_MEDIUM))
        layout.addWidget(self.message_label)
        
        from PyQt6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(scaler.get_ui_font(scaler.FONT_SIZE_SMALL))
        self.progress_bar.setMinimumHeight(scaler.value(24))
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        button_layout = QHBoxLayout()
        scaler.spacing(button_layout, scaler.SPACING_SMALL)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setFont(scaler.get_ui_font(scaler.FONT_SIZE_MEDIUM))
        self.cancel_button.setMinimumHeight(scaler.value(32))
        self.cancel_button.clicked.connect(self.on_cancel)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def setProgress(self, value):
        """
        Set the progress value (0-100).
        
        Args:
            value: Progress value
        """
        self.progress_bar.setValue(value)
    
    def setMessage(self, message):
        """
        Update the progress message.
        
        Args:
            message: New progress message
        """
        self.message_label.setText(message)
    
    def on_cancel(self):
        """Handle cancel button click."""
        self.canceled.emit()
        self.close()


class LogDisplay(QTextEdit):
    """Text display for logging with colored text support."""
    
    def __init__(self, scaler, parent=None):
        """
        Initialize a log display.
        
        Args:
            scaler: UIScaler instance for consistent sizing
            parent: Parent widget
        """
        super().__init__(parent)
        self.setReadOnly(True)
        
        # Set consistent monospace font
        self.setFont(scaler.get_code_font())
    
    def appendLog(self, text, log_type="info"):
        """
        Append log text with color based on type.
        
        Args:
            text: Log text
            log_type: Log type (info, error, warning, success)
        """
        # Use default text formatting from Fusion theme
        format = QTextCharFormat()
        
        # Add timestamp if not a data message
        from datetime import datetime
        if log_type.lower() not in ["rx", "tx"]:
            timestamp = f"[{datetime.now().strftime('%H:%M:%S')}] "
        else:
            timestamp = ""
        
        # Add text with format
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.setCharFormat(format)
        
        # Add prefix based on log type
        if log_type.lower() == "rx":
            prefix = "[RX] "
        elif log_type.lower() == "tx":
            prefix = "[TX] "
        elif log_type.lower() == "error":
            prefix = "[ERROR] "
        elif log_type.lower() == "warning":
            prefix = "[WARNING] "
        else:
            prefix = ""
        
        cursor.insertText(f"{timestamp}{prefix}{text}\n")
        
        # Auto-scroll to bottom
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
    
    def clear(self):
        """Clear the log display."""
        super().clear()


class PortSelector(QComboBox):
    """Combo box specifically for selecting serial ports."""
    
    def __init__(self, scaler, parent=None):
        """
        Initialize a port selector.
        
        Args:
            scaler: UIScaler instance for consistent sizing
            parent: Parent widget
        """
        super().__init__(parent)
        self.setFont(scaler.get_ui_font(scaler.FONT_SIZE_MEDIUM))
        self.setMinimumWidth(scaler.value(150))
        self.setMinimumHeight(scaler.value(28))
        self.refresh()
    
    def refresh(self):
        """Refresh the list of available ports."""
        import serial.tools.list_ports
        
        # Save current selection
        current = self.currentText()
        
        # Clear and update
        self.clear()
        ports = serial.tools.list_ports.comports()
        
        # Add ports to combo
        for port in ports:
            self.addItem(port.device)
        
        # Try to restore previous selection
        index = self.findText(current)
        if index >= 0:
            self.setCurrentIndex(index)


class FileSelector(QWidget):
    """Widget for selecting a file with browse button."""
    
    fileSelected = pyqtSignal(str)
    
    def __init__(self, scaler, label="File:", filter="All Files (*.*)", parent=None):
        """
        Initialize a file selector.
        
        Args:
            scaler: UIScaler instance for consistent sizing
            label: Label text
            filter: File filter string
            parent: Parent widget
        """
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        scaler.spacing(layout, scaler.SPACING_SMALL)
        
        self.label = QLabel(label)
        self.label.setFont(scaler.get_ui_font(scaler.FONT_SIZE_SMALL))
        
        self.path_input = QLineEdit()
        self.path_input.setFont(scaler.get_code_font())
        self.path_input.setMinimumHeight(scaler.value(28))
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setFont(scaler.get_ui_font(scaler.FONT_SIZE_MEDIUM))
        self.browse_button.setMinimumHeight(scaler.value(28))
        
        layout.addWidget(self.label)
        layout.addWidget(self.path_input, 1)  # Give input stretch priority
        layout.addWidget(self.browse_button)
        
        self.filter = filter
        self.browse_button.clicked.connect(self.browse)
    
    def browse(self):
        """Open file dialog to browse for a file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select File", "", self.filter
        )
        
        if path:
            self.path_input.setText(path)
            self.fileSelected.emit(path)
    
    def filePath(self):
        """Get the selected file path."""
        return self.path_input.text()
    
    def setFilePath(self, path):
        """Set the file path."""
        self.path_input.setText(path)


# You can add more custom widgets as needed