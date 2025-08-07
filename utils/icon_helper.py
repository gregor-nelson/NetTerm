"""
SVG Icon Helper for PyQt6 applications.
Provides simple SVG icon loading with Qt standard icon fallbacks.
"""

import os
import sys
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QStyle


def get_icon(name, fallback_standard_icon=None, size=16):
    """
    Load an SVG icon with Qt standard icon fallback.
    
    Args:
        name (str): Icon filename without extension (e.g., 'connect', 'refresh')
        fallback_standard_icon (QStyle.StandardPixmap): Qt standard icon to use as fallback
        size (int): Icon size in pixels
        
    Returns:
        QIcon: Loaded icon or fallback icon
    """
    # Determine the base path for assets
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # Running as script
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    icon_path = os.path.join(base_path, 'assets', 'icons', f'{name}.svg')
    
    # Try to load SVG icon
    if os.path.exists(icon_path):
        try:
            # Create QSvgRenderer and render to QPixmap
            renderer = QSvgRenderer(icon_path)
            if renderer.isValid():
                pixmap = QPixmap(QSize(size, size))
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                return QIcon(pixmap)
        except Exception:
            pass
    
    # Fallback to Qt standard icon if provided
    if fallback_standard_icon:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            return app.style().standardIcon(fallback_standard_icon)
    
    # Return empty icon as last resort
    return QIcon()


# Convenience functions for specific icons
def get_connect_icon(size=16):
    """Get connect/play icon."""
    return get_icon('connect', QStyle.StandardPixmap.SP_MediaPlay, size)


def get_refresh_icon(size=16):
    """Get refresh/reload icon."""
    return get_icon('refresh', QStyle.StandardPixmap.SP_BrowserReload, size)


def get_enter_icon(size=16):
    """Get enter/return icon."""
    return get_icon('enter', QStyle.StandardPixmap.SP_ArrowDown, size)


def get_escape_icon(size=16):
    """Get escape/cancel icon."""
    return get_icon('escape', QStyle.StandardPixmap.SP_DialogCancelButton, size)


def get_toggle_icon(checked=False, size=16):
    """Get toggle icon based on state."""
    if checked:
        return get_icon('toggle_on', QStyle.StandardPixmap.SP_DialogApplyButton, size)
    else:
        return get_icon('toggle_off', QStyle.StandardPixmap.SP_DialogCancelButton, size)


def get_clear_icon(size=16):
    """Get clear icon."""
    return get_icon('clear', QStyle.StandardPixmap.SP_LineEditClearButton, size)


def get_timestamp_icon(size=16):
    """Get timestamp/clock icon."""
    return get_icon('timestamp', QStyle.StandardPixmap.SP_ComputerIcon, size)


def get_hex_icon(size=16):
    """Get hex mode icon."""
    return get_icon('hex', QStyle.StandardPixmap.SP_ComputerIcon, size)


def get_auto_term_icon(size=16):
    """Get auto-termination icon."""
    return get_icon('auto_term', QStyle.StandardPixmap.SP_MediaSeekForward, size)


def get_filter_icon(size=16):
    """Get filter icon."""
    return get_icon('filter', QStyle.StandardPixmap.SP_DialogApplyButton, size)


def get_auto_clear_icon(size=16):
    """Get auto-clear icon."""
    return get_icon('auto_clear', QStyle.StandardPixmap.SP_BrowserReload, size)


def get_clear_all_icon(size=16):
    """Get clear all icon."""
    return get_icon('clear_all', QStyle.StandardPixmap.SP_DialogResetButton, size)


def get_send_icon(size=16):
    """Get send/transmit icon."""
    return get_icon('send', QStyle.StandardPixmap.SP_MediaSeekForward, size)


def get_history_icon(size=16):
    """Get history/list icon."""
    return get_icon('history', QStyle.StandardPixmap.SP_FileDialogDetailedView, size)