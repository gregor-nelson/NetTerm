"""
UI scaling utilities for responsive UI across different screen sizes.
"""
from PyQt6.QtCore import QSize, QRect
from PyQt6.QtGui import QScreen


class UIScaler:
    """Utility class for scaling UI components to match screen resolution."""
    
    def __init__(self, parent_widget=None):
        """
        Initialize the UIScaler.
        
        Args:
            parent_widget: The parent widget used to access the screen information.
                          If None, will try to use primary screen.
        """
        self.parent = parent_widget
        self.scale_factor = self.calculate_scale_factor()
        
        # Define font families for the application
        self.code_font = "Consolas"
        self.ui_font = "Segoe UI"
        
        # Define consistent spacing standards
        self.SPACING_SMALL = 4
        self.SPACING_MEDIUM = 8
        self.SPACING_LARGE = 12
        self.SPACING_SECTION = 16
        
        # Define consistent font sizes
        self.FONT_SIZE_SMALL = 8
        self.FONT_SIZE_MEDIUM = 9
        self.FONT_SIZE_LARGE = 11
        self.FONT_SIZE_CODE = 11
    
    def calculate_scale_factor(self):
        """
        Calculate UI scale factor based on screen resolution.
        
        Returns:
            float: The scaling factor to apply to UI elements
        """
        # Get primary screen
        if self.parent:
            screen = self.parent.screen()
        else:
            screen = QScreen.primaryScreen()
            
        if not screen:
            return 1.0  # Default if screen can't be detected
            
        # Get screen geometry and resolution
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        logical_dpi = screen.logicalDotsPerInch()
        
        # Calculate scale factor based on resolution and DPI
        # For screens smaller than 1280x720, scale down the UI
        base_scale = min(1, min(screen_width / 1280, screen_height / 720))
        
        # Additionally consider DPI for high-DPI screens
        dpi_scale = logical_dpi / 96.0  # 96 DPI is a common baseline
        
        # The final scale is influenced by both screen size and DPI
        # We use a weighted approach to prevent excessive scaling
        scale = base_scale * (dpi_scale * 0.5 + 0.5)
        
        # Clamp to reasonable values (0.6 to 1.4) to avoid extreme scaling
        scale = max(0.6, min(1.4, scale))
        
        print(f"Screen resolution: {screen_width}x{screen_height}, DPI: {logical_dpi}, Scale factor: {scale:.2f}")
        return scale
    
    def size(self, width, height):
        """
        Scale dimensions according to scale factor.
        
        Args:
            width: Original width
            height: Original height
            
        Returns:
            QSize: Scaled size
        """
        return QSize(int(width * self.scale_factor), int(height * self.scale_factor))
    
    def rect(self, x, y, width, height):
        """
        Scale a rectangle according to scale factor.
        
        Args:
            x: Original x coordinate
            y: Original y coordinate
            width: Original width
            height: Original height
            
        Returns:
            QRect: Scaled rectangle
        """
        return QRect(
            int(x * self.scale_factor), 
            int(y * self.scale_factor),
            int(width * self.scale_factor), 
            int(height * self.scale_factor)
        )
    
    def value(self, value):
        """
        Scale a single value according to scale factor.
        
        Args:
            value: Original numeric value
            
        Returns:
            int: Scaled value
        """
        return int(value * self.scale_factor)
    
    def margins(self, layout, left, top, right, bottom):
        """
        Set scaled margins on a layout.
        
        Args:
            layout: The Qt layout to modify
            left, top, right, bottom: Original margin values
        """
        layout.setContentsMargins(
            self.value(left),
            self.value(top),
            self.value(right),
            self.value(bottom)
        )
    
    def spacing(self, layout, spacing):
        """
        Set scaled spacing on a layout.
        
        Args:
            layout: The Qt layout to modify
            spacing: Original spacing value
        """
        layout.setSpacing(self.value(spacing))
    
    def get_code_font(self, size=None):
        """
        Get a properly configured code font.
        
        Args:
            size: Font size (uses FONT_SIZE_CODE if None)
            
        Returns:
            QFont: Configured code font
        """
        from PyQt6.QtGui import QFont
        font = QFont()
        font.setFamily(self.code_font)
        font.setPointSize(self.value(size or self.FONT_SIZE_CODE))
        font.setStyleHint(QFont.StyleHint.Monospace)
        return font
    
    def get_ui_font(self, size=None, weight=None):
        """
        Get a properly configured UI font.
        
        Args:
            size: Font size (uses FONT_SIZE_MEDIUM if None)
            weight: Font weight (QFont.Weight enum)
            
        Returns:
            QFont: Configured UI font
        """
        from PyQt6.QtGui import QFont
        font = QFont()
        font.setFamily(self.ui_font)
        font.setPointSize(self.value(size or self.FONT_SIZE_MEDIUM))
        if weight:
            font.setWeight(weight)
        return font
    
