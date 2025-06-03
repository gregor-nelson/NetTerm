"""
Enhanced theme configuration for Network Tools application.
Marine-inspired professional theme with industrial elements
optimized for offshore/maritime environments.
"""

# Define color palette - Professional Marine Theme
COLORS = {
    # Core colors
    "black": "#15191f",         # Deeper, more maritime black
    "white": "#e6edf3",         # Slightly bluer white for better contrast
    "darker": "#0d1117",        # Even darker background that feels like deep water
    
    # Blues - multiple tones for hierarchy
    "blue": "#2d8ccd",          # Main blue (less purple than current)
    "blue_dark": "#1b5f8f",     # Darker blue for secondary elements
    "blue_light": "#68b5e8",    # Lighter blue for highlights
    
    # Grays - more steps for better hierarchy
    "gray1": "#1e232d",         # Slightly bluer dark gray
    "gray2": "#2c3240",         # More pronounced mid-gray
    "gray3": "#465166",         # Higher contrast for better readability
    "gray4": "#6d8dad",         # Bluer gray for text
    
    # Accents
    "green": "#5cb176",         # More teal-leaning green
    "red": "#e05561",           # Maritime red (like port navigation lights)
    "orange": "#cd6e36",        # Maritime orange (like starboard navigation lights)
    "yellow": "#e2b340",        # Maritime signal yellow
    "teal": "#3d888c",          # Teal accent for variety
    
    # Borders
    "col_borderbar": "#15191f", # inner border
    "border_highlight": "#2d8ccd", # Highlighted border (blue)
    "border_normal": "#2c3240",  # Normal border
    
    # Status colors for direct reference in code
    "status_disconnected": "#e05561",  # Red
    "status_connected": "#5cb176",     # Green
    "status_waiting": "#e2b340",       # Yellow
    "status_error": "#cd6e36",         # Orange
    "status_active": "#2d8ccd",        # Blue
    "status_alert": "#cd6e36",         # Orange
    
    # Text colors for different data types
    "rx_text": "#2d8ccd",       # Blue for received data
    "tx_text": "#5cb176",       # Green for transmitted data
    "error_text": "#e05561",    # Red for error messages
    
    # UI interaction colors
    "special_key_hover": "#465166",  # Darker gray for key hover state
    "highlight_bg": "#222d40",    # Subtle highlight for hover states
    
    # Chart/visualization colors
    "chart_1": "#2d8ccd",       # Primary chart color
    "chart_2": "#5cb176",       # Secondary chart color
    "chart_3": "#e2b340",       # Tertiary chart color
    "chart_4": "#cd6e36",       # Quaternary chart color
}

def get_scaled_stylesheet(scale_factor, code_font, ui_font):
    """
    Generate a stylesheet with properly scaled dimensions
    
    Args:
        scale_factor: The UI scaling factor based on screen resolution
        code_font: Font family string for code/monospace text
        ui_font: Font family string for UI elements
        
    Returns:
        A complete stylesheet string with proper scaling
    """
    # Scale font sizes - reduced base sizes
    code_font_size = int(11 * scale_factor)
    ui_font_size = int(8 * scale_factor) 
    small_font_size = int(7 * scale_factor)
    
    # Scale padding and border values - more compact
    padding_xs = f"{int(1 * scale_factor)}px"
    padding_sm = f"{int(2 * scale_factor)}px"
    padding_md = f"{int(3 * scale_factor)}px"
    padding_lg = f"{int(5 * scale_factor)}px"
    
    # Scale margins - reduced
    margin_sm = f"{int(2 * scale_factor)}px"
    margin_md = f"{int(4 * scale_factor)}px"
    
    # Scale widget dimensions - more compact widths
    min_button_width = f"{int(60 * scale_factor)}px"
    combo_min_width = f"{int(70 * scale_factor)}px"
    
    # Scale icon and control sizes - smaller icons
    icon_size = f"{int(12 * scale_factor)}px"
    
    # Border radius - using a small value for a more industrial look
    border_radius = f"{int(1 * scale_factor)}px"
    
    # Border width - consistent with industrial designs
    border_width = f"{int(1 * scale_factor)}px"
    border_highlight = f"{int(2 * scale_factor)}px"
    
    c = COLORS  # Shorthand for colors
    
    return f"""
        /* Global Application Styling */
        QMainWindow {{ 
            background-color: {c["black"]}; 
            border: {border_width} solid {c["gray2"]};
            font-size: {ui_font_size}pt; /* Base font size for the entire application */
        }}
        
        QWidget {{
            background-color: {c["black"]};
            color: {c["white"]};
        }}
        
        /* Tooltip styling */
        QToolTip {{
            background-color: {c["gray1"]};
            color: {c["white"]};
            border: {border_width} solid {c["blue"]};
            padding: {padding_sm};
            opacity: 220;
            font-family: '{ui_font}';
            font-size: {small_font_size}pt;
        }}
        
        /* Text handling widgets */
        QTextEdit {{ 
            background-color: {c["darker"]}; 
            color: {c["white"]}; 
            border: {border_width} solid {c["gray3"]};
            border-radius: {border_radius};
            padding: {padding_lg};
            font-family: '{code_font}';
            font-size: {code_font_size}pt;
            line-height: 1.5;
            selection-background-color: {c["blue_dark"]};
            selection-color: {c["white"]};
        }}
        
        QLineEdit {{ 
            background-color: {c["darker"]}; 
            color: {c["white"]}; 
            border: {border_width} solid {c["gray3"]};
            border-radius: {border_radius};
            padding: {padding_sm} {padding_lg};
            font-family: '{code_font}';
            font-size: {ui_font_size}pt;
            selection-background-color: {c["blue_dark"]};
            selection-color: {c["white"]};
        }}
        
        QLineEdit:focus {{ 
            border: {border_width} solid {c["blue"]};
        }}
        
        /* Button styling with consistent marine theme */
        QPushButton {{ 
            background-color: {c["gray2"]}; 
            color: {c["white"]}; 
            border: {border_width} solid {c["gray3"]};
            border-radius: {border_radius};
            padding: {padding_md} {padding_lg};
            min-width: {min_button_width};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
            font-weight: bold;
            text-align: center;
        }}
        
        QPushButton:hover {{ 
            background-color: {c["highlight_bg"]}; 
            color: {c["white"]};
            border-left: {border_highlight} solid {c["blue"]};
        }}
        
        QPushButton:pressed {{ 
            background-color: {c["blue_dark"]}; 
            color: {c["white"]};
        }}
        
        QPushButton:checked {{
            background-color: {c["gray3"]};
            color: {c["white"]};
            border-left: {border_highlight} solid {c["blue"]};
        }}
        
        QPushButton:disabled {{
            background-color: {c["gray1"]};
            color: {c["gray3"]};
            border: {border_width} solid {c["gray2"]};
        }}
        
        /* Label styling */
        QLabel {{ 
            color: {c["gray4"]}; 
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
            margin-bottom: {margin_sm};
        }}
        
        /* Dropdown styling */
        QComboBox {{
            background-color: {c["darker"]};
            color: {c["white"]};
            border: {border_width} solid {c["gray3"]};
            border-radius: {border_radius};
            padding: {padding_sm} {padding_lg};
            min-width: {combo_min_width};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
        }}
        
        QComboBox:focus {{
            border: {border_width} solid {c["blue"]};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: {int(20 * scale_factor)}px;
            background: {c["gray2"]};
            border-radius: 0;
        }}
        
        QComboBox::down-arrow {{
            image: url(:/icons/dropdown.png);
            width: {icon_size};
            height: {icon_size};
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {c["darker"]};
            color: {c["white"]};
            selection-background-color: {c["blue"]};
            selection-color: {c["white"]};
            border: {border_width} solid {c["gray3"]};
        }}
        
        /* Status bar styling */
        QStatusBar {{ 
            background-color: {c["gray1"]}; 
            color: {c["white"]};
            font-family: '{ui_font}';
            font-size: {small_font_size}pt;
            padding: {padding_xs};
            border-top: {border_width} solid {c["gray3"]};
        }}
        
        /* Tab styling for multi-view interfaces */
        QTabWidget::pane {{ 
            border: {border_width} solid {c["gray3"]};
            background-color: {c["black"]};
            border-top: {border_highlight} solid {c["blue"]};
        }}
        
        QTabBar::tab {{ 
            background-color: {c["gray2"]}; 
            color: {c["gray4"]}; 
            padding: {padding_sm} {int(10 * scale_factor)}px;
            border-top-left-radius: {border_radius};
            border-top-right-radius: {border_radius};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
            min-width: {int(60 * scale_factor)}px;
            margin-right: {margin_sm};
        }}
        
        QTabBar::tab:selected {{ 
            background-color: {c["black"]}; 
            color: {c["white"]};
            border-top: {border_highlight} solid {c["blue"]};
        }}
        
        QTabBar::tab:hover:!selected {{ 
            background-color: {c["highlight_bg"]}; 
            color: {c["white"]};
        }}
        
        /* Group box styling */
        QGroupBox {{ 
            border: {border_width} solid {c["gray3"]};
            border-radius: {border_radius};
            margin-top: {int(14 * scale_factor)}px;
            padding-top: {padding_md};
            font-family: '{ui_font}';
            font-size: {int(9 * scale_factor)}pt;
            color: {c["blue_light"]};
            font-weight: bold;
        }}
        
        QGroupBox::title {{ 
            subcontrol-origin: margin;
            left: {padding_lg};
            top: {padding_sm};
            padding: 0px {padding_lg} 0px {padding_lg};
            background-color: {c["gray2"]};
        }}
        
        /* Progress bar styling */
        QProgressBar {{
            border: {border_width} solid {c["gray3"]};
            border-radius: {border_radius};
            background-color: {c["darker"]};
            color: {c["white"]};
            text-align: center;
            font-family: '{ui_font}';
            font-size: {small_font_size}pt;
            height: {int(16 * scale_factor)}px;
        }}
        
        QProgressBar::chunk {{
            background-color: {c["blue"]};
            width: {padding_lg};
        }}
        
        /* Table styling */
        QTableWidget {{
            background-color: {c["darker"]};
            color: {c["white"]};
            border: {border_width} solid {c["gray3"]};
            gridline-color: {c["gray3"]};
            font-family: '{code_font}';
            font-size: {int(11 * scale_factor)}pt;
            selection-background-color: {c["blue_dark"]};
            selection-color: {c["white"]};
        }}
        
        QTableWidget::item {{
            padding: {padding_sm};
        }}
        
        QTableWidget::item:selected {{
            background-color: {c["blue_dark"]};
        }}
        
        QHeaderView::section {{
            background-color: {c["gray2"]};
            color: {c["white"]};
            padding: {padding_sm};
            border: {border_width} solid {c["gray3"]};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
            font-weight: bold;
        }}
        
        /* Checkbox styling */
        QCheckBox {{
            color: {c["white"]};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
            spacing: {padding_md};
            padding: {padding_sm};
        }}
        
        QCheckBox::indicator {{
            width: {int(12 * scale_factor)}px;
            height: {int(12 * scale_factor)}px;
            border: {border_width} solid {c["gray3"]};
            border-radius: {border_radius};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {c["blue"]};
            border: {border_width} solid {c["blue"]};
            image: url(:/icons/check.png);
        }}
        
        QCheckBox::indicator:unchecked {{
            background-color: {c["darker"]};
            border: {border_width} solid {c["gray3"]};
        }}
        
        QCheckBox::indicator:hover {{
            border: {border_width} solid {c["blue_light"]};
        }}
        
        /* Spinbox styling */
        QSpinBox, QDoubleSpinBox {{
            background-color: {c["darker"]};
            color: {c["white"]};
            border: {border_width} solid {c["gray3"]};
            border-radius: {border_radius};
            padding: {padding_xs} {padding_lg};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
        }}
        
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border: {border_width} solid {c["blue"]};
        }}
        
        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
            background-color: {c["gray2"]};
            border: {border_width} solid {c["gray3"]};
            border-radius: 0;
            width: {int(16 * scale_factor)}px;
            height: {int(12 * scale_factor)}px;
        }}
        
        QSpinBox::up-button:hover, QSpinBox::down-button:hover,
        QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {c["highlight_bg"]};
        }}
        
        QSpinBox::up-button:pressed, QSpinBox::down-button:pressed,
        QDoubleSpinBox::up-button:pressed, QDoubleSpinBox::down-button:pressed {{
            background-color: {c["blue_dark"]};
        }}
        
        /* Radio button styling */
        QRadioButton {{
            color: {c["white"]};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
            spacing: {padding_md};
            padding: {padding_sm};
        }}
        
        QRadioButton::indicator {{
            width: {int(12 * scale_factor)}px;
            height: {int(12 * scale_factor)}px;
            border: {border_width} solid {c["gray3"]};
            border-radius: {int(6 * scale_factor)}px;
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {c["blue"]};
            border: {border_width} solid {c["blue"]};
            image: url(:/icons/radio.png);
        }}
        
        QRadioButton::indicator:unchecked {{
            background-color: {c["darker"]};
            border: {border_width} solid {c["gray3"]};
        }}
        
        QRadioButton::indicator:hover {{
            border: {border_width} solid {c["blue_light"]};
        }}
        
        /* Scrollbar styling for a cleaner look */
        QScrollBar:vertical {{
            background-color: {c["darker"]};
            width: {int(8 * scale_factor)}px;
            margin: {int(6 * scale_factor)}px 0 {int(6 * scale_factor)}px 0;
            border-radius: {border_radius};
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {c["gray3"]};
            border-radius: {border_radius};
            min-height: {int(20 * scale_factor)}px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {c["blue"]};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        
        QScrollBar:horizontal {{
            background-color: {c["darker"]};
            height: {int(8 * scale_factor)}px;
            margin: 0 {int(6 * scale_factor)}px 0 {int(6 * scale_factor)}px;
            border-radius: {border_radius};
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {c["gray3"]};
            border-radius: {border_radius};
            min-width: {int(20 * scale_factor)}px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {c["blue"]};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
        
        /* Menu styling */
        QMenuBar {{
            background-color: {c["gray1"]};
            color: {c["white"]};
            border-bottom: {border_width} solid {c["gray3"]};
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: {padding_sm} {padding_lg};
        }}
        
        QMenuBar::item:selected {{
            background-color: {c["blue"]};
            color: {c["white"]};
        }}
        
        QMenu {{
            background-color: {c["gray1"]};
            color: {c["white"]};
            border: {border_width} solid {c["gray3"]};
            padding: {padding_xs};
        }}
        
        QMenu::item {{
            padding: {padding_sm} {int(20 * scale_factor)}px {padding_sm} {padding_lg};
        }}
        
        QMenu::item:selected {{
            background-color: {c["blue"]};
            color: {c["white"]};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {c["gray3"]};
            margin: {padding_xs} 0;
        }}
        
        /* Splitter styling */
        QSplitter::handle {{
            background-color: {c["gray3"]};
        }}
        
        QSplitter::handle:horizontal {{
            width: {int(2 * scale_factor)}px;
        }}
        
        QSplitter::handle:vertical {{
            height: {int(2 * scale_factor)}px;
        }}
        
        QSplitter::handle:hover {{
            background-color: {c["blue"]};
        }}
        
        /* Specific widget styles with marine theme colors */
        #rxDisplay, #txDisplay {{ 
            font-family: '{code_font}';
            font-size: {code_font_size}pt;
            border-left: {int(3 * scale_factor)}px solid {c["gray3"]};
            background-color: {c["darker"]};
        }}
        
        #rxDisplay {{ 
            border-left-color: {c["rx_text"]};
        }}
        
        #txDisplay {{ 
            border-left-color: {c["tx_text"]};
        }}
        
        /* Action buttons with maritime colors */
        #connectButton {{ 
            background-color: {c["green"]};
            color: {c["black"]};
            font-weight: bold;
        }}
        
        #connectButton:hover {{ 
            background-color: {c["status_connected"]};
            border: {border_width} solid {c["white"]};
        }}
        
        #transmitButton, #sendButton {{ 
            background-color: {c["blue"]};
            color: {c["black"]};
            font-weight: bold;
        }}
        
        #transmitButton:hover, #sendButton:hover {{ 
            background-color: {c["blue_light"]};
            border: {border_width} solid {c["white"]};
        }}
        
        #clearAllButton {{ 
            background-color: {c["red"]};
            color: {c["white"]};
        }}
        
        #clearAllButton:hover {{ 
            background-color: {c["status_disconnected"]};
            border: {border_width} solid {c["white"]};
        }}
        
        /* Specialized buttons */
        #specialKey {{ 
            min-width: {int(50 * scale_factor)}px;
            padding: {padding_sm};
            border: {border_width} solid {c["gray3"]};
            background-color: {c["gray2"]};
        }}
        
        #specialKey:hover {{ 
            background-color: {c["special_key_hover"]};
            border-left: {border_highlight} solid {c["blue"]};
        }}
        
        #toggleButton {{ 
            min-width: {int(70 * scale_factor)}px;
            background-color: {c["gray2"]};
        }}
        
        #toggleButton:checked {{ 
            background-color: {c["blue_dark"]};
            border-left: {border_highlight} solid {c["blue"]};
        }}
        
        /* Command input - maritime style */
        #commandInput {{
            background-color: {c["darker"]};
            color: {c["white"]};
            border: {border_width} solid {c["gray3"]};
            border-radius: {border_radius};
            padding: {padding_md};
            font-family: '{code_font}';
            font-size: {ui_font_size}pt;
        }}
        
        #commandInput:focus {{
            border: {border_width} solid {c["blue"]};
        }}
        
        /* Icon buttons - compact square style */
        #iconButton {{
            min-width: {int(22 * scale_factor)}px;
            min-height: {int(22 * scale_factor)}px;
            padding: {padding_xs};
            font-weight: bold;
            border-radius: {border_radius};
        }}
        
        /* Clear button - simple action */
        #clearButton {{
            min-width: {int(60 * scale_factor)}px;
            background-color: {c["gray3"]};
        }}
        
        #clearButton:hover {{
            background-color: {c["red"]};
            color: {c["white"]};
        }}
        
        /* Labels with maritime theme */
        #sectionLabel {{
            color: {c["blue_light"]};
            font-weight: bold;
            padding-bottom: {padding_sm};
            border-bottom: 1px solid {c["gray3"]};
        }}
        
        #displayTitle {{
            color: {c["blue"]};
            font-weight: bold;
            font-size: {int(11 * scale_factor)}pt;
        }}
        
        #statsLabel {{
            color: {c["gray4"]};
            font-size: {small_font_size}pt;
        }}
        
        #statusLabel {{
            font-weight: bold;
        }}
        
        #actionButton {{
            background-color: {c["gray3"]};
            min-width: {int(70 * scale_factor)}px;
        }}
        
        #actionButton:hover {{
            background-color: {c["blue_dark"]};
        }}

        /* Status indicators for connection states with maritime colors */
        #connection_status_connected {{
            color: {c["status_connected"]};
            font-weight: bold;
        }}
        
        #connection_status_disconnected {{
            color: {c["status_disconnected"]};
            font-weight: bold;
        }}
        
        #connection_status_waiting {{
            color: {c["status_waiting"]};
            font-weight: bold;
        }}
        
        #connection_status_error {{
            color: {c["status_error"]};
            font-weight: bold;
        }}
        
        /* Panel styling with improved separation */
        #topPanel, #ioPanel, #bottomPanel {{
            background-color: {c["black"]};
            border: none;
            margin: {margin_sm};
        }}
        
        #connectionGroup, #sequenceGroup, #keysGroup, #toggleGroup {{
            background-color: {c["black"]};
        }}
        
        #displayHeader {{
            background-color: {c["gray2"]};
            padding: {padding_sm};
            border-top-left-radius: {border_radius};
            border-top-right-radius: {border_radius};
            border-bottom: {border_width} solid {c["blue"]};
        }}
        
        #rxPanel, #txPanel {{
            background-color: {c["black"]};
            margin: {margin_sm};
            border: {border_width} solid {c["gray3"]};
            border-radius: {border_radius};
        }}
    """

def get_light_theme(scale_factor, code_font, ui_font):
    """
    Generate a light marine theme stylesheet for daylight operations
    
    Args:
        scale_factor: The UI scaling factor based on screen resolution
        code_font: Font family string for code/monospace text
        ui_font: Font family string for UI elements
        
    Returns:
        A complete stylesheet string with proper scaling
    """
    # Define light theme color palette - Maritime Day Mode
    colors = {
        # Core colors
        "black": "#2c3e50",         # Deep blue-gray
        "white": "#ffffff",         # Pure white
        "darker": "#1c2e40",        # Darker navy for contrast
        
        # Blues - multiple tones for hierarchy
        "blue": "#2980b9",          # Maritime blue
        "blue_dark": "#2c3e50",     # Darker blue for secondary elements
        "blue_light": "#3498db",    # Lighter blue for highlights
        
        # Grays - more steps for better hierarchy
        "gray1": "#ecf0f1",         # Very light gray (almost white)
        "gray2": "#d6dbdf",         # Light gray
        "gray3": "#bdc3c7",         # Medium gray
        "gray4": "#7f8c8d",         # Darker gray for text
        
        # Accents
        "green": "#27ae60",         # Maritime green
        "red": "#e74c3c",           # Maritime red
        "orange": "#e67e22",        # Maritime orange
        "yellow": "#f1c40f",        # Maritime yellow
        "teal": "#16a085",          # Teal accent
        
        # Status colors
        "status_disconnected": "#e74c3c",  # Red
        "status_connected": "#27ae60",     # Green
        "status_waiting": "#f1c40f",       # Yellow
        "status_error": "#e67e22",         # Orange
        "status_active": "#2980b9",        # Blue
        "status_alert": "#e67e22",         # Orange
        
        # Text colors
        "rx_text": "#2980b9",       # Blue for received data
        "tx_text": "#27ae60",       # Green for transmitted data
        "error_text": "#e74c3c",    # Red for error messages
        
        # UI colors
        "highlight_bg": "#eef5fb",  # Very light blue highlight
        "border_highlight": "#2980b9",
        "border_normal": "#bdc3c7",
    }
    
    # Scale dimensions - using more compact sizing
    code_font_size = int(11 * scale_factor)
    ui_font_size = int(8 * scale_factor)
    small_font_size = int(7 * scale_factor)
    
    padding_xs = f"{int(2 * scale_factor)}px"
    padding_sm = f"{int(4 * scale_factor)}px"
    padding_md = f"{int(6 * scale_factor)}px"
    padding_lg = f"{int(8 * scale_factor)}px"
    
    margin_sm = f"{int(4 * scale_factor)}px"
    
    min_button_width = f"{int(80 * scale_factor)}px"
    combo_min_width = f"{int(90 * scale_factor)}px"
    
    border_radius = f"{int(2 * scale_factor)}px"
    border_width = f"{int(1 * scale_factor)}px"
    border_highlight = f"{int(2 * scale_factor)}px"
    
    c = colors
    
    # Return light theme stylesheet (similar structure to dark theme)
    return f"""
        /* Global Application Styling - Light Marine Theme */
        QMainWindow {{ 
            background-color: {c["gray1"]}; 
            border: {border_width} solid {c["gray3"]};
        }}
        
        QWidget {{
            background-color: {c["gray1"]};
            color: {c["black"]};
        }}
        
        /* Similar styling to the dark theme but with light colors */
        /* ... */
        
        /* This is abbreviated - the full implementation would mirror
           the dark theme structure but with the light color palette */
    """

def get_night_vision_theme(scale_factor, code_font, ui_font):
    """
    Generate a red-tinted night vision theme for nighttime operations
    that preserves night vision - crucial for maritime night operations
    
    Args:
        scale_factor: The UI scaling factor based on screen resolution
        code_font: Font family string for code/monospace text
        ui_font: Font family string for UI elements
        
    Returns:
        A complete stylesheet string with proper scaling
    """
    # Define night vision theme color palette (red-tinted)
    colors = {
        # Core colors - primarily red-tinted for night vision preservation
        "black": "#0a0000",         # Very dark red-black
        "white": "#ff9e9e",         # Light red instead of white
        "darker": "#050000",        # Even darker background
        
        # Special night vision friendly colors
        "primary": "#dd0000",       # Main accent (red)
        "dim_red": "#660000",       # Dimmer red for secondary elements
        "highlight": "#ff0000",     # Brighter red for highlights
        
        # Status colors - all in red spectrum to preserve night vision
        "status_inactive": "#330000",   # Dark red
        "status_active": "#bb0000",     # Medium red
        "status_alert": "#ff0000",      # Bright red
        
        # Grays - red-tinted
        "gray1": "#1a0a0a",         # Very dark red-gray
        "gray2": "#2a0f0f",         # Dark red-gray
        "gray3": "#3a1515",         # Medium red-gray
        "gray4": "#601a1a",         # Light red-gray
    }
    
    # Scale factors - same as other themes
    # ...
    
    # Return red-tinted night vision stylesheet
    # ...