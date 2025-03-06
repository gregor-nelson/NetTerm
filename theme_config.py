"""
Theme configuration for Network Tools application.
Defines colors, styles, and generates stylesheets with proper scaling.
"""

# Define color palette - One Dark theme
COLORS = {
    "black": "#1e222a",
    "white": "#abb2bf",
    "gray2": "#2e323a",  # unfocused window border
    "gray3": "#545862",
    "gray4": "#6d8dad",
    "blue": "#61afef",   # focused window border
    "green": "#7EC7A2",
    "red": "#e06c75",
    "orange": "#caaa6a",
    "yellow": "#EBCB8B",
    "pink": "#c678dd",
    "darker": "#171a21",  # Even darker background for contrast
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
    # Scale font sizes
    code_font_size = int(14 * scale_factor)
    ui_font_size = int(10 * scale_factor)
    small_font_size = int(9 * scale_factor)
    
    # Scale padding and border values
    padding_sm = f"{int(4 * scale_factor)}px"
    padding_md = f"{int(6 * scale_factor)}px"
    padding_lg = f"{int(8 * scale_factor)}px"
    
    # Scale widget dimensions
    min_button_width = f"{int(80 * scale_factor)}px"
    combo_min_width = f"{int(90 * scale_factor)}px"
    
    c = COLORS  # Shorthand for colors
    
    return f"""
        QMainWindow {{ 
            background-color: {c["black"]}; 
            border: 1px solid {c["gray2"]};
        }}
        QTextEdit {{ 
            background-color: {c["black"]}; 
            color: {c["white"]}; 
            border: 1px solid {c["gray3"]};
            padding: {padding_lg};
            font-family: '{code_font}';
            font-size: {code_font_size}pt;
            line-height: 1.5;
        }}
        QLineEdit {{ 
            background-color: {c["black"]}; 
            color: {c["white"]}; 
            border: 1px solid {c["gray3"]};
            border-radius: {padding_sm};
            padding: {padding_sm} {padding_lg};
            font-family: '{code_font}';
            font-size: {ui_font_size}pt;
        }}
        QPushButton {{ 
            background-color: {c["gray2"]}; 
            color: {c["white"]}; 
            border: 1px solid {c["gray3"]};
            border-radius: {padding_sm};
            padding: {padding_md} {padding_lg};
            min-width: {min_button_width};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
        }}
        QPushButton:hover {{ 
            background-color: {c["gray3"]}; 
            color: {c["white"]};
        }}
        QPushButton:pressed {{ 
            background-color: {c["blue"]}; 
            color: {c["black"]};
        }}
        QPushButton:checked {{
            background-color: {c["blue"]};
            color: {c["black"]};
        }}
        QLabel {{ 
            color: {c["gray4"]}; 
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
            margin-bottom: 2px;
        }}
        QComboBox {{
            background-color: {c["black"]};
            color: {c["white"]};
            border: 1px solid {c["gray3"]};
            border-radius: {padding_sm};
            padding: {padding_sm} {padding_lg};
            min-width: {combo_min_width};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
        }}
        QComboBox::drop-down {{
            border: none;
            width: {int(20 * scale_factor)}px;
            background: {c["gray2"]};
            border-top-right-radius: {padding_sm};
            border-bottom-right-radius: {padding_sm};
        }}
        QComboBox QAbstractItemView {{
            background-color: {c["black"]};
            color: {c["white"]};
            selection-background-color: {c["blue"]};
            selection-color: {c["black"]};
            border: 1px solid {c["gray3"]};
        }}
        QStatusBar {{ 
            background-color: {c["gray2"]}; 
            color: {c["white"]};
            font-family: '{ui_font}';
            font-size: {small_font_size}pt;
            padding: 3px;
        }}
        QTabWidget::pane {{ 
            border: 1px solid {c["gray3"]};
            background-color: {c["black"]};
        }}
        QTabBar::tab {{ 
            background-color: {c["gray2"]}; 
            color: {c["gray4"]}; 
            padding: {padding_lg} {int(16 * scale_factor)}px;
            border-top-left-radius: {padding_sm};
            border-top-right-radius: {padding_sm};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
        }}
        QTabBar::tab:selected {{ 
            background-color: {c["black"]}; 
            color: {c["white"]};
            border-bottom: 2px solid {c["blue"]};
        }}
        QTabBar::tab:hover:!selected {{ 
            background-color: {c["gray3"]}; 
            color: {c["white"]};
        }}
        QGroupBox {{ 
            border: 1px solid {c["gray3"]};
            border-radius: {padding_sm};
            margin-top: {padding_lg};
            padding-top: {padding_lg};
            font-family: '{ui_font}';
            font-size: {int(11 * scale_factor)}pt;
            color: {c["gray4"]};
        }}
        QGroupBox::title {{ 
            subcontrol-origin: margin;
            left: {padding_lg};
            padding: 0px {padding_lg} 0px {padding_lg};
        }}
        QProgressBar {{
            border: 1px solid {c["gray3"]};
            border-radius: {padding_sm};
            background-color: {c["black"]};
            color: {c["white"]};
            text-align: center;
            font-family: '{ui_font}';
            font-size: {small_font_size}pt;
        }}
        QProgressBar::chunk {{
            background-color: {c["blue"]};
            width: {padding_lg};
        }}
        QTableWidget {{
            background-color: {c["black"]};
            color: {c["white"]};
            border: 1px solid {c["gray3"]};
            gridline-color: {c["gray3"]};
            font-family: '{code_font}';
            font-size: {int(11 * scale_factor)}pt;
        }}
        QTableWidget::item {{
            padding: {padding_sm};
        }}
        QHeaderView::section {{
            background-color: {c["gray2"]};
            color: {c["white"]};
            padding: {padding_sm};
            border: 1px solid {c["gray3"]};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
            font-weight: bold;
        }}
        QCheckBox {{
            color: {c["white"]};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
            spacing: {padding_lg};
        }}
        QCheckBox::indicator {{
            width: {int(16 * scale_factor)}px;
            height: {int(16 * scale_factor)}px;
            border: 1px solid {c["gray3"]};
            border-radius: 2px;
        }}
        QCheckBox::indicator:checked {{
            background-color: {c["blue"]};
            border: 1px solid {c["blue"]};
        }}
        QCheckBox::indicator:unchecked {{
            background-color: {c["black"]};
            border: 1px solid {c["gray3"]};
        }}
        QSpinBox {{
            background-color: {c["black"]};
            color: {c["white"]};
            border: 1px solid {c["gray3"]};
            border-radius: {padding_sm};
            padding: 2px {padding_lg};
            font-family: '{ui_font}';
            font-size: {ui_font_size}pt;
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            background-color: {c["gray2"]};
            border: 1px solid {c["gray3"]};
            border-radius: 2px;
            width: {int(16 * scale_factor)}px;
            height: {int(12 * scale_factor)}px;
        }}
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
            background-color: {c["gray3"]};
        }}
        
        /* Specific widget styles */
        #rxDisplay, #txDisplay {{ 
            font-family: '{code_font}';
            font-size: {code_font_size}pt;
        }}
        
        #connectButton {{ 
            background-color: {c["green"]};
            color: {c["black"]};
            font-weight: bold;
        }}
        
        #transmitButton {{ 
            background-color: {c["blue"]};
            color: {c["black"]};
            font-weight: bold;
        }}
        
        #clearAllButton {{ 
            background-color: {c["red"]};
            color: {c["white"]};
        }}
        
        #specialKey {{ 
            min-width: {int(50 * scale_factor)}px;
            padding: {padding_sm};
        }}
        
        #toggleButton {{ 
            min-width: {int(70 * scale_factor)}px;
        }}
    """


# Additional theme variants could be defined here
def get_light_theme(scale_factor, code_font, ui_font):
    """Generate a light theme stylesheet"""
    # Implementation for light theme would go here
    pass