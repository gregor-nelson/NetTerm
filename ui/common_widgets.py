"""
Common reusable UI widgets for the Network Tools application.
These widgets maintain consistent styling and behavior across the application.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QPushButton, QLineEdit, QLabel, QGroupBox, 
                           QVBoxLayout, QHBoxLayout, QDialog, QMessageBox,
                           QTextEdit, QFileDialog, QComboBox, QWidget,
                           QProgressBar)
from PyQt6.QtGui import QIcon, QFont, QColor, QTextCursor, QTextCharFormat


class StyledButton(QPushButton):
    """Button with consistent styling and optional icon support."""
    
    def __init__(self, text, icon=None, accent=False, destructive=False, parent=None):
        """
        Initialize a styled button.
        
        Args:
            text: Button text
            icon: Optional icon name (without extension)
            accent: Whether this is an accent (primary) button
            destructive: Whether this is a destructive action button
            parent: Parent widget
        """
        super().__init__(text, parent)
        
        self.setObjectName("accentButton" if accent else 
                          "destructiveButton" if destructive else "")
        
        if icon:
            self.setIcon(QIcon(f"icons/{icon}.png"))


class LabeledInput(QGroupBox):
    """Input field with a label for form layouts."""
    
    def __init__(self, label_text, placeholder="", parent=None):
        """
        Initialize a labeled input.
        
        Args:
            label_text: Label text
            placeholder: Input placeholder text
            parent: Parent widget
        """
        super().__init__(parent)
        self.setTitle("")  # No title for the group box
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.label = QLabel(label_text)
        self.label.setObjectName("formLabel")
        
        self.input = QLineEdit()
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
    
    STATUS_COLORS = {
        "online": "#7EC7A2",  # Green
        "offline": "#e06c75",  # Red
        "warning": "#EBCB8B",  # Yellow
        "default": "#abb2bf"   # Light gray
    }
    
    def __init__(self, parent=None):
        """
        Initialize a status indicator.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setStatus("default", "Status")
    
    def setStatus(self, status_type, text):
        """
        Set the status with appropriate color.
        
        Args:
            status_type: Status type (online, offline, warning, default)
            text: Status text
        """
        color = self.STATUS_COLORS.get(status_type.lower(), self.STATUS_COLORS["default"])
        self.setText(text)
        self.setStyleSheet(f"color: {color}; font-weight: bold;")


class ProgressDialog(QDialog):
    """Dialog showing progress with cancel option."""
    
    canceled = pyqtSignal()
    
    def __init__(self, title, message, parent=None):
        """
        Initialize a progress dialog.
        
        Args:
            title: Dialog title
            message: Progress message
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        self.message_label = QLabel(message)
        layout.addWidget(self.message_label)
        
        from PyQt6.QtWidgets import QProgressBar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        button_layout = QHBoxLayout()
        self.cancel_button = QPushButton("Cancel")
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
    
    def __init__(self, parent=None):
        """
        Initialize a log display.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setReadOnly(True)
        
        # Set monospace font
        font = QFont("Consolas, Menlo, Courier, monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
    
    def appendLog(self, text, log_type="info"):
        """
        Append log text with color based on type.
        
        Args:
            text: Log text
            log_type: Log type (info, error, warning, success)
        """
        # Define colors for different log types
        colors = {
            "info": QColor("#abb2bf"),     # Light gray
            "error": QColor("#e06c75"),    # Red
            "warning": QColor("#EBCB8B"),  # Yellow
            "success": QColor("#7EC7A2"),  # Green
            "rx": QColor("#7EC7A2"),       # Green for received data
            "tx": QColor("#61afef")        # Blue for transmitted data
        }
        
        # Get appropriate color
        color = colors.get(log_type.lower(), colors["info"])
        
        # Create text format with color
        format = QTextCharFormat()
        format.setForeground(color)
        
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
    
    def __init__(self, parent=None):
        """
        Initialize a port selector.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setMinimumWidth(150)
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
    
    def __init__(self, label="File:", filter="All Files (*.*)", parent=None):
        """
        Initialize a file selector.
        
        Args:
            label: Label text
            filter: File filter string
            parent: Parent widget
        """
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.label = QLabel(label)
        self.path_input = QLineEdit()
        self.browse_button = QPushButton("Browse...")
        
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