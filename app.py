#!/usr/bin/env python3
"""
Network Tools - Serial monitor and ping scanning utility.
Main application entry point.
Features:
- Serial port communication interface
- Network ping scanner with port scanning capabilities
"""
import sys
from PyQt6.QtWidgets import QApplication

from ui.main_window import NetworkToolsWindow


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Set the application style to Fusion for consistent cross-platform theming
    # To test Windows style, comment out the line above and uncomment the line below:
    # app.setStyle('Windows')
    app.setStyle('Fusion')
    
    # Create main window
    window = NetworkToolsWindow()
    
    # Show the window and start the application
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
