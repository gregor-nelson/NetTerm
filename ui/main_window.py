"""
Main application window that composes all UI components.
"""
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTabWidget, QStatusBar
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon  # Import QIcon for setting the window icon
import sys
import os

from ui.scaling import UIScaler
from ui.serial_tab import SerialTab
from ui.ping_tab import PingTab
from ui.serial_port_scanner import SerialPortScannerTab  # Import our new tab

# Function to handle resource paths for bundled files
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class NetworkToolsWindow(QMainWindow):
    """Main application window for Network Tools."""
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        # Initialize UI scaler
        self.ui_scaler = UIScaler(self)
        
        self.setWindowTitle("Network Tools")
        
        # Set the window icon (for taskbar and title bar)
        self.setWindowIcon(QIcon(resource_path("icon.ico")))  # Path to your .ico file
        
        # Use scaled geometry instead of fixed size
        scaled_width = self.ui_scaler.value(1000)
        scaled_height = self.ui_scaler.value(700)
        self.setGeometry(100, 100, scaled_width, scaled_height)
        
        # Set minimum size to prevent UI from becoming too small
        min_width = self.ui_scaler.value(800)
        min_height = self.ui_scaler.value(600)
        self.setMinimumSize(min_width, min_height)
        
        # Make the window resizable
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)
        
        # Set up the main layout
        self.init_ui()
    
    def init_ui(self):
        """Initialize the application UI."""
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        
        # Apply consistent spacing standards
        self.ui_scaler.spacing(main_layout, 8)  # Medium spacing
        self.ui_scaler.margins(main_layout, 12, 12, 12, 12)  # Medium margins
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create tab components
        self.serial_tab = SerialTab(self.ui_scaler)
        self.serial_port_scanner_tab = SerialPortScannerTab(self.ui_scaler)  # Add our new tab
        self.ping_tab = PingTab(self.ui_scaler)
        
        # Connect signals from tabs to main window
        self.serial_tab.status_message.connect(self.show_status_message)
        self.serial_tab.error_occurred.connect(self.show_error)
        self.serial_port_scanner_tab.status_message.connect(self.show_status_message)  # Connect new tab signals
        self.serial_port_scanner_tab.error_occurred.connect(self.show_error)
        self.ping_tab.status_message.connect(self.show_status_message)
        self.ping_tab.error_occurred.connect(self.show_error)
        
        # Add tabs with consistent styling
        self.tabs.addTab(self.serial_tab, "Serial Monitor")
        self.tabs.addTab(self.serial_port_scanner_tab, "Serial Port Scanner")
        self.tabs.addTab(self.ping_tab, "Ping Scanner")
        
        # Apply consistent tab widget font
        from PyQt6.QtGui import QFont
        ui_font = QFont(self.ui_scaler.ui_font)
        ui_font.setPointSize(self.ui_scaler.value(9))
        self.tabs.setFont(ui_font)
        
        main_layout.addWidget(self.tabs)
        
        # Status Bar with consistent font
        self.status_bar = QStatusBar()
        status_font = self.ui_scaler.get_ui_font(self.ui_scaler.FONT_SIZE_SMALL)
        self.status_bar.setFont(status_font)
        self.setStatusBar(self.status_bar)
    
    def show_status_message(self, message, timeout=3000):
        """Show a status message with optional timeout."""
        self.status_bar.showMessage(message, timeout)
    
    def show_error(self, message):
        """Show an error message in the status bar."""
        self.status_bar.showMessage(f"ERROR: {message}", 5000)
    
    
    def closeEvent(self, event):
        """Handle application close event."""
        # Close any open connections from tabs
        try:
            if hasattr(self.serial_tab, 'toggle_connection'):
                self.serial_tab.toggle_connection()
            
            # Stop the scan timer in the serial port scanner tab
            if hasattr(self.serial_port_scanner_tab, 'scan_timer'):
                self.serial_port_scanner_tab.scan_timer.stop()
            
            if hasattr(self.ping_tab, 'stop_ping_scan'):
                self.ping_tab.stop_ping_scan()
        except:
            # Don't prevent closing if cleanup fails
            pass
            
        event.accept()