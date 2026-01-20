"""
Centralized Stylesheet for Strategy Builder UI

This module provides a consistent dark theme stylesheet for all Strategy Builder
windows, dialogs, and panels. All UI components should import and use these styles.

Author: Strategy Builder Team
Date: 2026-01-18
"""

# Main application stylesheet - extracted from strategy_builder_main_window.py
MAIN_STYLESHEET = """
    QMainWindow {
        background-color: #15191E;
    }
    QWidget {
        background-color: #15191E;
        color: #E8EAED;
    }
    QDialog {
        background-color: #15191E;
        color: #E8EAED;
    }
    QGroupBox {
        background-color: #1E2128;
        border: 1px solid #3C4149;
        border-radius: 8px;
        margin-top: 20px;
        padding-top: 35px;
        color: #E8EAED;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 5px;
        color: #095983;
        font-size: 12pt !important;
        font-weight: bold;
    }
    QLineEdit {
        background-color: #2A2F3A;
        border: 1px solid #3C4149;
        border-radius: 6px;
        padding: 8px;
        color: #E8EAED;
    }
    QLineEdit:focus {
        border-color: #2070FF;
    }
    QComboBox {
        background-color: #2A2F3A;
        border: 1px solid #3C4149;
        border-radius: 6px;
        padding: 6px 10px;
        color: #E8EAED;
    }
    QComboBox:hover {
        border-color: #2070FF;
    }
    QComboBox::drop-down {
        border: none;
        background: transparent;
    }
    QComboBox QAbstractItemView {
        background-color: #2A2F3A;
        border: none;
        selection-background-color: #2070FF;
        alternate-background-color: #2A2F3A;
        color: #E8EAED;
        outline: none;
        show-decoration-selected: 0;
        gridline-color: #2A2F3A;
        spacing: 0px;
    }
    QComboBox QAbstractItemView::item {
        background-color: #2A2F3A;
        color: #E8EAED;
        padding: 6px 8px;
        margin: 0px;
        border: none;
        border-top: none;
        border-bottom: none;
        spacing: 0px;
    }
    QComboBox QAbstractItemView::item:selected {
        background-color: #2070FF;
        color: #FFFFFF;
        border: 0px solid transparent;
        margin: 0px;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: #374151;
        border: 0px solid transparent;
        margin: 0px;
    }
    QTextEdit {
        background-color: #2A2F3A;
        border: 1px solid #3C4149;
        border-radius: 6px;
        padding: 8px;
        color: #BDC1C6;
    }
    QLabel {
        color: #E8EAED;
        background: transparent;
    }
    QScrollArea {
        background-color: #15191E;
        border: none;
    }
    QScrollBar:vertical {
        background-color: #1E2128;
        width: 12px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background-color: #3C4149;
        border-radius: 6px;
        min-height: 20px;
    }
    QScrollBar::handle:vertical:hover {
        background-color: #4A5058;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QSplitter::handle {
        background-color: #3C4149;
    }
    QSplitter::handle:horizontal {
        width: 2px;
    }
    QSplitter::handle:vertical {
        height: 2px;
    }
    QMenuBar {
        background-color: #1E2128;
        color: #E8EAED;
        border-bottom: 1px solid #3C4149;
    }
    QMenuBar::item:selected {
        background-color: #2A2F3A;
    }
    QMenu {
        background-color: #2A2F3A;
        border: 1px solid #3C4149;
        color: #E8EAED;
    }
    QMenu::item:selected {
        background-color: #2070FF;
    }
    QToolBar {
        background-color: #1E2128;
        border-bottom: 1px solid #3C4149;
        border-top: 1px solid #3C4149;
        spacing: 8px;
        padding: 8px 4px;
        margin-top: 4px;
    }
    QToolButton {
        background: transparent;
        border: none;
        color: #A0AEC0;
        padding: 6px;
    }
    QToolButton:hover {
        background-color: #2A2F3A;
        border-radius: 2px;
    }
    QToolButton:pressed {
        background-color: #374151;
    }
    QStatusBar {
        background-color: #1E2128;
        color: #9AA0A6;
        border-top: 1px solid #3C4149;
    }
    QSpinBox {
        background-color: #2A2F3A;
        border: 1px solid #3C4149;
        border-radius: 6px;
        padding: 6px;
        color: #E8EAED;
    }
    QSpinBox:hover {
        border-color: #2070FF;
    }
    QSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        background-color: #3C4149;
        border: none;
        border-radius: 3px;
    }
    QSpinBox::up-button:hover {
        background-color: #4A5058;
    }
    QSpinBox::up-arrow {
        image: none;
        width: 0px;
        height: 0px;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-bottom: 5px solid #6B7280;
    }
    QSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        background-color: #3C4149;
        border: none;
        border-radius: 3px;
    }
    QSpinBox::down-button:hover {
        background-color: #4A5058;
    }
    QSpinBox::down-arrow {
        image: none;
        width: 0px;
        height: 0px;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 5px solid #6B7280;
    }
    QProgressBar {
        background-color: #2A2F3A;
        border: 1px solid #3C4149;
        border-radius: 6px;
        text-align: center;
        color: #E8EAED;
    }
    QProgressBar::chunk {
        background-color: #2070FF;
        border-radius: 5px;
    }
    QPushButton {
        background-color: #3C4149;
        color: #E8EAED;
        border: none;
        border-radius: 6px;
        padding: 8px 16px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #4A5058;
    }
    QPushButton:pressed {
        background-color: #2A2F3A;
    }
    QPushButton:disabled {
        background-color: #2A2F3A;
        color: #6B7280;
    }
    QRadioButton::indicator {
        width: 18px;
        height: 18px;
        border-radius: 9px;
        border: 2px solid #3C4149;
        background-color: transparent;
    }
    QRadioButton::indicator:unchecked {
        background-color: #2A2F3A;
        border: 2px solid #3C4149;
    }
    QRadioButton::indicator:unchecked:hover {
        border: 2px solid #4A5058;
    }
    QRadioButton::indicator:checked {
        background-color: #214fa2;
        border: 2px solid #214fa2;
    }
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 3px;
        border: 2px solid #3C4149;
        background-color: #2A2F3A;
    }
    QCheckBox::indicator:unchecked:hover {
        border: 2px solid #4A5058;
    }
    QCheckBox::indicator:checked {
        background-color: #214fa2;
        border: 2px solid #214fa2;
        image: url(none);
    }
    QToolTip {
        background-color: #374151;
        color: #E8EAED;
        border: 1px solid #3C4149;
        border-radius: 6px;
        padding: 8px;
        font-size: 24px;
    }
"""

# Color palette for consistent theming
COLORS = {
    # Background colors
    'bg_dark': '#15191E',
    'bg_medium': '#1E2128',
    'bg_secondary': '#1E2128',  # Alias for bg_medium (table headers, panels)
    'bg_light': '#2A2F3A',
    'bg_input': '#2A2F3A',

    # Border colors
    'border': '#3C4149',
    'border_focus': '#2070FF',
    
    # Text colors
    'text_primary': '#E8EAED',
    'text_secondary': '#BDC1C6',
    'secondary': '#BDC1C6',  # Alias for text_secondary (message categories, labels)
    'text_muted': '#9AA0A6',
    'text_label': '#A0AEC0',
    
    # Status colors
    'success': '#10B981',
    'warning': '#FFA500',
    'error': '#C35252',
    'info': '#2070FF',
    
    # Button colors
    'button_primary': '#2a5eb8',  # User specified blue for position numbers and REQUIRED badge
    'button_primary_hover': '#1A3A70',
    'button_success': '#10B981',
    'button_success_hover': '#059669',
    'button_danger': '#C35252',
    'button_danger_hover': '#A63F3F',
    'button_secondary': '#3C4149',
    'button_secondary_hover': '#4A5058',
    
    # Stepper colors (for tabs and step indicators)
    'stepper_inactive': '#374151',
    'stepper_active': '#204486',
    'stepper_hover': '#4B5563',
    'stepper_complete': '#10B981',
    'stepper_error': '#C35252',
}

# Standardized label styling (used throughout main window)
LABEL_STYLES = {
    'default': f"color: {COLORS['text_primary']};",
    'muted': f"color: {COLORS['text_label']};",  # #A0AEC0
    'secondary': f"color: {COLORS['text_secondary']};",
    'error': f"color: {COLORS['error']};",
    'success': f"color: {COLORS['success']};",
    'warning': f"color: {COLORS['warning']};",
}

# Standardized radio button styling (matches main window Bullish/Bearish)
RADIO_BUTTON_STYLES = {
    'bullish': f"QRadioButton {{ color: {COLORS['success']}; background: transparent; }}",
    'bearish': f"QRadioButton {{ color: {COLORS['error']}; background: transparent; }}",
    'default': f"QRadioButton {{ color: {COLORS['text_primary']}; background: transparent; }}",
    'info': f"QRadioButton {{ color: {COLORS['info']}; background: transparent; }}",
}

# Standardized checkbox styling (transparent background)
CHECKBOX_STYLES = {
    'default': f"QCheckBox {{ color: {COLORS['text_primary']}; background: transparent; }}",
    'success': f"QCheckBox {{ color: {COLORS['success']}; background: transparent; }}",
    'error': f"QCheckBox {{ color: {COLORS['error']}; background: transparent; }}",
}

# Tab widget styling (stepper-like appearance)
TAB_WIDGET_STYLESHEET = f"""
    QTabWidget::pane {{
        border: 1px solid {COLORS['border']};
        background: {COLORS['bg_dark']};
        margin-top: 10px;
    }}
    QTabBar::tab {{
        background: {COLORS['stepper_inactive']};
        color: {COLORS['text_primary']};
        padding: 15px 30px;
        margin-right: 4px;
        margin-top: 8px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        font-weight: bold;
        min-width: 120px;
    }}
    QTabBar::tab:selected {{
        background: {COLORS['stepper_active']};
        color: #FFFFFF;
    }}
    QTabBar::tab:hover:!selected {{
        background: {COLORS['stepper_hover']};
        color: #FFFFFF;
    }}
"""


def get_main_stylesheet() -> str:
    """
    Get the main application stylesheet.
    
    Returns:
        Complete stylesheet string for main application
    """
    return MAIN_STYLESHEET


def get_label_style(style_type: str = 'default') -> str:
    """
    Get standardized label styling.
    
    Args:
        style_type: Type of label style ('default', 'muted', 'error', etc.)
    
    Returns:
        CSS style string for label
    """
    return LABEL_STYLES.get(style_type, LABEL_STYLES['default'])


def get_radio_button_style(style_type: str = 'default') -> str:
    """
    Get standardized radio button styling.
    
    Args:
        style_type: Type of radio button ('bullish', 'bearish', 'default', 'info')
    
    Returns:
        CSS style string for radio button
    """
    return RADIO_BUTTON_STYLES.get(style_type, RADIO_BUTTON_STYLES['default'])


def get_checkbox_style(style_type: str = 'default') -> str:
    """
    Get standardized checkbox styling.
    
    Args:
        style_type: Type of checkbox ('default', 'success', 'error')
    
    Returns:
        CSS style string for checkbox
    """
    return CHECKBOX_STYLES.get(style_type, CHECKBOX_STYLES['default'])


def get_tab_widget_stylesheet() -> str:
    """
    Get standardized tab widget stylesheet.
    
    Returns:
        CSS style string for tab widgets
    """
    return TAB_WIDGET_STYLESHEET


def get_color(color_name: str) -> str:
    """
    Get a color value from the palette.
    
    Args:
        color_name: Name of the color (e.g., 'bg_dark', 'text_primary', 'success')
    
    Returns:
        Hex color string
    """
    return COLORS.get(color_name, COLORS['text_primary'])


def get_primary_button_stylesheet(compact=False) -> str:
    """
    Get stylesheet for primary action buttons.
    
    Args:
        compact: If True, uses smaller padding (8px 16px vs 10px 20px)
    
    Returns:
        Button stylesheet string
    """
    padding = "8px 16px" if compact else "10px 20px"
    radius = "4px" if compact else "6px"
    return f"""
        QPushButton {{
            background-color: {COLORS['button_primary']};
            color: white;
            font-weight: bold;
            padding: {padding};
            border-radius: {radius};
            min-width: 120px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['button_primary_hover']};
        }}
        QPushButton:pressed {{
            background-color: #1550DF;
        }}
        QPushButton:disabled {{
            background-color: #555555;
            color: #888888;
        }}
    """


def get_success_button_stylesheet() -> str:
    """Get stylesheet for success/confirm buttons."""
    return f"""
        QPushButton {{
            background-color: {COLORS['button_success']};
            color: white;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 6px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['button_success_hover']};
        }}
    """


def get_danger_button_stylesheet() -> str:
    """Get stylesheet for danger/delete buttons."""
    return f"""
        QPushButton {{
            background-color: {COLORS['button_danger']};
            color: white;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 6px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['button_danger_hover']};
        }}
    """


def get_spinbox_button_stylesheet() -> str:
    """Get stylesheet for spinbox up/down buttons - custom blue up, gray down, blue hover."""
    return f"""
        QSpinBox::up-button {{
            background-color: #1e283a;
            border: 1px solid #1e283a;
            border-radius: 2px;
            width: 20px;
            subcontrol-origin: border;
            subcontrol-position: top right;
        }}
        QSpinBox::up-button:hover {{
            background-color: {COLORS['button_primary']};
            border-color: {COLORS['button_primary']};
        }}
        QSpinBox::down-button {{
            background-color: #4A5058;
            border: 1px solid #4A5058;
            border-radius: 2px;
            width: 20px;
            subcontrol-origin: border;
            subcontrol-position: bottom right;
        }}
        QSpinBox::down-button:hover {{
            background-color: {COLORS['button_primary']};
            border-color: {COLORS['button_primary']};
        }}
        QSpinBox::up-arrow {{
            image: none;
            width: 0;
            height: 0;
            border: none;
        }}
        QSpinBox::down-arrow {{
            image: none;
            width: 0;
            height: 0;
            border: none;
        }}
    """


def get_panel_title_stylesheet() -> str:
    """Get stylesheet for panel titles (matches main window 'Strategy Information' style)."""
    return f"""
        color: #095983;
        font-size: 12pt;
        font-weight: bold;
    """


def get_groupbox_header_stylesheet() -> str:
    """Get stylesheet for groupbox headers (column titles)."""
    return f"""
        QGroupBox {{
            color: {COLORS['text_muted']};
            font-weight: bold;
            border: 1px solid {COLORS['border']};
            border-radius: 2px;
            margin-top: 8px;
            padding-top: 10px;
        }}
        QGroupBox::title {{
            color: {COLORS['text_muted']};
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }}
    """


def get_preset_day_button_stylesheet() -> str:
    """
    Get stylesheet for preset day selection buttons (30, 60, 90, etc).
    
    Optimized for compact inline display with hover/pressed states.
    
    Returns:
        Button stylesheet string
    """
    return """
        QPushButton {
            background-color: #1E293B;
            color: #CBD5E1;
            border: 1px solid #334155;
            border-radius: 2px;
            font-size: 8pt;
            font-weight: normal;
        }
        QPushButton:hover {
            background-color: #2563EB;
            color: white;
            border-color: #3B82F6;
        }
        QPushButton:pressed {
            background-color: #1D4ED8;
        }
    """


def get_separator_stylesheet() -> str:
    """Get stylesheet for horizontal separator lines."""
    return f"background-color: {COLORS['border']}; max-height: 1px; margin: 10px 0;"


def get_secondary_button_stylesheet() -> str:
    """Get stylesheet for secondary/cancel buttons."""
    return f"""
        QPushButton {{
            background-color: {COLORS['button_secondary']};
            color: white;
            font-weight: bold;
            padding: 10px 24px;
            border-radius: 2px;
            min-width: 100px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['button_secondary_hover']};
        }}
    """


def get_status_label_style(status='default') -> str:
    """Get styled status label for success/error/warning states."""
    colors = {
        'success': COLORS['success'],  # #10B981
        'error': COLORS['error'],      # #C35252
        'warning': COLORS['warning'],  # #FFA500
        'info': COLORS['info'],        # #2070FF
        'default': COLORS['text_muted']
    }
    return f"color: {colors.get(status, colors['default'])}; font-weight: bold;"


def get_logic_badge_style(badge_type='required') -> str:
    """
    Get logic badge styling for Required/Optional/AND/OR indicators.
    
    Args:
        badge_type: Type of badge ('required', 'optional', 'and', 'or')
    
    Returns:
        CSS style string for logic badges
    """
    bg_colors = {
        'required': COLORS['button_primary'],    # Blue background #2a5eb8
        'optional': '#007a51',                   # Dark green background (user specified)
        'and': COLORS['info'],                   # Blue background
        'or': COLORS['warning']                  # Orange background
    }
    
    text_colors = {
        'required': '#FFFFFF',                   # White text for maximum contrast
        'optional': '#FFFFFF',                   # White text for maximum contrast
        'and': 'white',
        'or': 'white'
    }
    
    bg_color = bg_colors.get(badge_type, bg_colors['required'])
    text_color = text_colors.get(badge_type, text_colors['required'])
    
    return f"""
        QLabel {{
            background-color: {bg_color};
            color: {text_color};
            font-weight: bold;
            padding: 2px 8px;
            border-radius: 2px;
            font-size: 8pt;
        }}
    """


def get_block_label_style(signal_direction='neutral') -> str:
    """
    Get block signal label styling for Bullish/Bearish/Neutral labels.
    
    Args:
        signal_direction: Direction ('bullish', 'bearish', 'neutral')
    
    Returns:
        CSS style string for block labels
    """
    colors = {
        'bullish': COLORS['success'],      # Green
        'bearish': COLORS['error'],        # Red
        'neutral': COLORS['text_muted']    # Gray
    }
    return f"color: {colors.get(signal_direction, colors['neutral'])}; font-weight: bold;"


def get_position_label_style(position='entry') -> str:
    """
    Get position label styling for Entry/Exit/Both indicators.
    
    Args:
        position: Position type ('entry', 'exit', 'both')
    
    Returns:
        CSS style string for position labels
    """
    colors = {
        'entry': COLORS['success'],     # Green
        'exit': COLORS['error'],        # Red
        'both': COLORS['info']          # Blue
    }
    return f"color: {colors.get(position, colors['entry'])}; font-weight: bold;"


def get_expand_button_style() -> str:
    """Get expand/collapse button styling for block panels."""
    return f"""
        QPushButton {{
            background: transparent;
            border: none;
            color: {COLORS['text_muted']};
            font-weight: bold;
            text-align: left;
            padding: 2px;
        }}
        QPushButton:hover {{
            color: {COLORS['info']};
        }}
    """


def get_remove_button_style() -> str:
    """Get remove/delete button styling (small red cross buttons)."""
    return f"""
        QPushButton {{
            background-color: {COLORS['button_danger']};
            color: white;
            border-radius: 3px;
            font-weight: bold;
            padding: 2px 6px;
            max-width: 20px;
            max-height: 20px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['button_danger_hover']};
        }}
    """


def get_add_button_style() -> str:
    """Get add button styling for adding blocks/signals."""
    return f"""
        QPushButton {{
            background-color: {COLORS['button_success']};
            color: white;
            font-weight: bold;
            padding: 6px 16px;
            border-radius: 6px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['button_success_hover']};
        }}
    """


def get_icon_button_style() -> str:
    """Get styling for small icon buttons (config, settings, etc.)."""
    return f"""
        QPushButton {{
            background: transparent;
            border: none;
            color: {COLORS['text_muted']};
            padding: 4px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['bg_light']};
            border-radius: 2px;
            color: {COLORS['text_primary']};
        }}
    """


def get_recheck_button_stylesheet() -> str:
    """
    Get stylesheet for Recheck On Delayed Candles button.
    
    Uses darker gray/blue styling to distinguish from primary Config button.
    
    Returns:
        Button stylesheet string with darker gray/blue theme
    """
    return """
        QPushButton {
            background-color: #3C4756;
            color: #B8C5D6;
            border: 1px solid #4A5568;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #4A5568;
            border-color: #5A6678;
        }
        QPushButton:pressed {
            background-color: #2D3748;
        }
    """


def get_table_stylesheet() -> str:
    """
    Get comprehensive table stylesheet for data tables.
    
    Returns:
        Complete QTableWidget stylesheet with headers, rows, selection
    """
    return f"""
        QTableWidget {{
            background-color: {COLORS['bg_dark']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border']};
            gridline-color: {COLORS['border']};
            selection-background-color: {COLORS['info']}40;
            selection-color: {COLORS['text_primary']};
        }}
        QTableWidget::item {{
            padding: 8px;
        }}
        QHeaderView::section {{
            background-color: {COLORS['bg_secondary']};
            color: {COLORS['text_primary']};
            padding: 12px;
            border: 1px solid {COLORS['border']};
            font-weight: 600;
        }}
    """


def get_text_edit_stylesheet() -> str:
    """
    Get stylesheet for QTextEdit output displays.
    
    Returns:
        QTextEdit stylesheet with dark theme and monospace font
    """
    return f"""
        QTextEdit {{
            background-color: {COLORS['bg_dark']};
            color: {COLORS['text_primary']};
            border: 1px solid {COLORS['border']};
            padding: 8px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 12px;
        }}
    """


def get_scroll_area_stylesheet() -> str:
    """
    Get stylesheet for QScrollArea.
    
    Returns:
        QScrollArea stylesheet with dark theme
    """
    return f"""
        QScrollArea {{
            background-color: {COLORS['bg_dark']};
            border: 1px solid {COLORS['border']};
        }}
    """
