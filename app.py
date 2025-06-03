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
from theme_config import get_scaled_stylesheet


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    
    # Create main window
    window = NetworkToolsWindow()
    
    # Get and apply the theme
    stylesheet = get_scaled_stylesheet(
        scale_factor=window.ui_scaler.scale_factor,
        code_font=window.ui_scaler.code_font,
        ui_font=window.ui_scaler.ui_font
    )
    window.apply_theme(stylesheet)
    
    # Show the window and start the application
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()