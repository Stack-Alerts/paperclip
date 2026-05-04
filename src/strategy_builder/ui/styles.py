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
    QSpinBox, QDoubleSpinBox {
        background-color: #2A2F3A;
        border: 1px solid #3C4149;
        border-radius: 6px;
        padding: 6px;
        color: #E8EAED;
    }
    QSpinBox:hover, QDoubleSpinBox:hover {
        border-color: #2070FF;
    }
    QSpinBox::up-button, QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 20px;
        background-color: #3C4149;
        border: none;
        border-radius: 3px;
    }
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
        background-color: #4A5058;
    }
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        image: none;
        width: 0px;
        height: 0px;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-bottom: 5px solid #6B7280;
    }
    QSpinBox::down-button, QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 20px;
        background-color: #3C4149;
        border: none;
        border-radius: 3px;
    }
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
        background-color: #4A5058;
    }
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
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
    'orange': '#a25c51',
    'aqua': '#51a292',
    
    # Status colors
    'success': '#10B981',
    'warning': '#FFA500',
    'error': '#C35252',
    'info': '#2070FF',
    
    # Panel / column title color (also used by QGroupBox::title and get_panel_title_stylesheet)
    'panel_title': '#095983',

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
    
    # Exit condition specific colors (Sprint 1.9.1)
    'exit_strategy_level': '#2070FF',           # Blue - STRATEGY-level exits
    'exit_block_level': '#10B981',              # Green - BLOCK-level exits
    'exit_signal_level': '#FFA500',             # Yellow - SIGNAL-level exits
    'exit_cumulative_tp_only': '#9AA0A6',       # Gray (0% - TP-only)
    'exit_cumulative_hybrid': '#2070FF',        # Blue (1-99% - Hybrid)
    'exit_cumulative_full': '#10B981',          # Green (100% - Full exit)
    'exit_cumulative_multiple': '#FFA500',      # Yellow (101-500% - Multiple opportunities)
    'exit_cumulative_high': '#FF6B6B',          # Orange (>500% - High redundancy)
    'dead_code_strikethrough': '#6B7280',       # Gray for disabled signals
}

# Standardized label styling (used throughout main window)
LABEL_STYLES = {
    'default': f"color: {COLORS['text_muted']};",  # Changed to muted to match Config tab
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
    'default': f"QCheckBox {{ color: {COLORS['text_muted']}; background: transparent; }}",
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


def get_italic_label_style(style_type: str = 'muted') -> str:
    """
    Get standardized italic label styling.

    Args:
        style_type: Type of label style ('default', 'muted', 'error', etc.)

    Returns:
        CSS style string for italic label
    """
    base = LABEL_STYLES.get(style_type, LABEL_STYLES['default'])
    return base + " font-style: italic;"


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
            text-align: center;
            qproperty-iconSize: 16px 16px;
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


def get_danger_button_stylesheet() -> str:
    """Get stylesheet for danger/delete buttons."""
    return f"""
        QPushButton {{
            background-color: {COLORS['button_danger']};
            color: white;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 6px;
            min-width: 100px;
        }}
        QPushButton:hover {{
            background-color: {COLORS['button_danger_hover']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['button_danger']};
        }}
    """


def get_recheck_remove_button_stylesheet() -> str:
    """Get stylesheet for RECHECK remove icon button (red, 40x40px)."""
    return get_recheck_small_icon_button_stylesheet('danger')


def get_success_button_stylesheet() -> str:
    """Get stylesheet for success/confirm buttons."""
    return f"""
        QPushButton {{
            background-color: {COLORS['button_success']};
            color: white;
            font-weight: bold;
            padding: 10px 20px;
            border-radius: 6px;
            min-width: 120px;
            text-align: center;
        }}
        QPushButton:hover {{
            background-color: {COLORS['button_success_hover']};
        }}
        QPushButton:pressed {{
            background-color: {COLORS['button_success']};
        }}
        QPushButton:disabled {{
            background-color: #555555;
            color: #888888;
        }}
    """


def get_spinbox_button_stylesheet() -> str:
    """Get stylesheet for spinbox up/down buttons - custom blue up, gray down, blue hover.
    
    Applies to both QSpinBox and QDoubleSpinBox for UI consistency.
    """
    return f"""
        QSpinBox::up-button, QDoubleSpinBox::up-button {{
            background-color: #1e283a;
            border: 1px solid #1e283a;
            border-radius: 2px;
            width: 20px;
            subcontrol-origin: border;
            subcontrol-position: top right;
        }}
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {{
            background-color: {COLORS['button_primary']};
            border-color: {COLORS['button_primary']};
        }}
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background-color: #4A5058;
            border: 1px solid #4A5058;
            border-radius: 2px;
            width: 20px;
            subcontrol-origin: border;
            subcontrol-position: bottom right;
        }}
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background-color: {COLORS['button_primary']};
            border-color: {COLORS['button_primary']};
        }}
        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
            image: none;
            width: 0;
            height: 0;
            border: none;
        }}
        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
            image: none;
            width: 0;
            height: 0;
            border: none;
        }}
    """


def get_panel_title_stylesheet() -> str:
    """Get stylesheet for panel titles (matches main window 'Strategy Information' style)."""
    return f"""
        color: {COLORS['panel_title']};
        font-size: 12pt;
        font-weight: bold;
    """


def get_column_title_stylesheet() -> str:
    """Get stylesheet for column/section titles in the Strategy Browser detail panel."""
    return f"color: {COLORS['panel_title']}; padding-bottom: 8px;"


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
            padding: 10px 20px;
            border-radius: 6px;
            min-width: 120px;
            text-align: center;
        }}
        QPushButton:hover {{
            background-color: {COLORS['button_secondary_hover']};
        }}
        QPushButton:disabled {{
            background-color: #555555;
            color: #888888;
        }}
    """


def get_status_label_style(status='default') -> str:
    """Get styled status label for success/error/warning states."""
    colors = {
        'success': COLORS['success'],  # #10B981
        'error': COLORS['error'],      # #C35252
        'warning': COLORS['warning'],  # #FFA500
        'info': COLORS['info'],        # #2070FF
        'default': COLORS['text_muted'],
        'orange': COLORS['orange'],  #a25c51
        'aqua': COLORS['aqua'],      #51a292
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
            background-color: #244647;
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


def get_recheck_small_icon_button_stylesheet(button_type='primary') -> str:
    """
    Get unified stylesheet for small RECHECK icon buttons (40x40px square).
    
    All three buttons (gear, duplicate, remove) use this with different colors.
    
    Args:
        button_type: 'primary' (teal/gear), 'success' (dark teal/duplicate), or 'danger' (red/remove)
    
    Returns:
        Button stylesheet string with consistent sizing and styling
    """
    colors_map = {
        'primary': {
            'bg': '#244647',
            'hover': '#1a3334',
            'pressed': '#0f2021'
        },
        'success': {
            'bg': '#1e5b5f',
            'hover': '#154447',
            'pressed': '#0c2c2e'
        },
        'danger': {
            'bg': COLORS['button_danger'],
            'hover': COLORS['button_danger_hover'],
            'pressed': '#A63F3F'
        }
    }
    
    color_set = colors_map.get(button_type, colors_map['primary'])
    
    return f"""
        QPushButton {{
            background-color: {color_set['bg']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 0px;
            font-size: 26px;
            font-weight: bold;
            min-width: 40px;
            max-width: 40px;
            min-height: 40px;
            max-height: 40px;
        }}
        QPushButton:hover {{
            background-color: {color_set['hover']};
        }}
        QPushButton:pressed {{
            background-color: {color_set['pressed']};
        }}
    """


def get_recheck_gear_button_stylesheet() -> str:
    """Get stylesheet for RECHECK gear icon button (blue, 40x40px)."""
    return get_recheck_small_icon_button_stylesheet('primary')


def get_recheck_duplicate_button_stylesheet() -> str:
    """Get stylesheet for RECHECK duplicate icon button (green, 40x40px)."""
    return get_recheck_small_icon_button_stylesheet('success')


def get_dialog_stylesheet() -> str:
    """Get stylesheet for dialog windows."""
    return f"""
        QDialog {{
            background-color: {COLORS['bg_dark']};
            color: {COLORS['text_primary']};
        }}
    """


def get_radio_container_stylesheet() -> str:
    """Get stylesheet for radio button container frame."""
    return f"""
        QFrame {{
            background-color: {COLORS['bg_light']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 10px;
        }}
    """


def get_signal_radio_stylesheet() -> str:
    """Get stylesheet for signal validation radio button."""
    return f"""
        QRadioButton {{
            color: {COLORS['text_primary']};
            font-weight: bold;
            padding: 5px;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid {COLORS['button_success']};
        }}
        QRadioButton::indicator:checked {{
            background-color: {COLORS['button_success']};
        }}
    """


def get_recheck_radio_stylesheet() -> str:
    """Get stylesheet for recheck validation radio button."""
    return f"""
        QRadioButton {{
            color: {COLORS['text_primary']};
            font-weight: bold;
            padding: 5px;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid {COLORS['button_primary']};
        }}
        QRadioButton::indicator:checked {{
            background-color: {COLORS['button_primary']};
        }}
    """


def get_table_stylesheet() -> str:
    """
    Get comprehensive table stylesheet for data tables.
    
    Returns:
        Complete QTableWidget stylesheet with headers, rows, selection, hover
    """
    return f"""
        QTableWidget {{
            background-color: {COLORS['bg_dark']};
            alternate-background-color: {COLORS['bg_medium']};
            color: {COLORS['text_muted']};
            border: 1px solid {COLORS['border']};
            gridline-color: {COLORS['border']};
            selection-background-color: #053336;
            selection-color: {COLORS['text_muted']};
        }}
        QTableWidget::item {{
            padding: 12px 8px;
            background-color: transparent;
        }}
        QTableWidget::item:hover {{
            background-color: #021a1e;
        }}
        QHeaderView::section {{
            background-color: {COLORS['bg_secondary']};
            color: {COLORS['text_muted']};
            padding: 14px 12px;
            border: 1px solid {COLORS['border']};
            font-weight: 600;
        }}
        QHeaderView::section:hover {{
            background-color: #252b36;
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


def get_transparent_scroll_area_stylesheet() -> str:
    """
    Get stylesheet for borderless, transparent QScrollArea.

    Use inside dialogs/tabs where the scroll area background should inherit
    from the parent widget rather than adding its own border.
    """
    return "QScrollArea { border: none; background: transparent; }"


def get_input_field_stylesheet() -> str:
    """
    Get stylesheet for QLineEdit input fields.
    
    NAUTILUS EXPERT: Used for Starting Capital and other numeric inputs
    
    Returns:
        QLineEdit stylesheet with dark theme and focus state
    """
    return f"""
        QLineEdit {{
            background-color: {COLORS['bg_input']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 8px;
            color: {COLORS['text_primary']};
            font-size: 10pt;
        }}
        QLineEdit:focus {{
            border-color: {COLORS['border_focus']};
        }}
        QLineEdit:hover {{
            border-color: {COLORS['border_focus']};
        }}
    """


def create_font(size: int = 10, bold: bool = False):
    """
    Create a standardized QFont for UI elements.

    Args:
        size: Font size in points (default: 10)
        bold: Whether font should be bold (default: False)

    Returns:
        QFont object with specified properties
    """
    from PyQt5.QtGui import QFont
    # CRITICAL: Must specify font family, otherwise Qt uses tiny default
    font = QFont("Segoe UI, Arial, sans-serif", size)
    if bold:
        font.setBold(True)
    return font


def set_hand_cursor(widget):
    """
    Set hand cursor for clickable widget.
    
    NAUTILUS EXPERT: Centralized hand cursor for professional UI polish.
    Apply to all buttons, tabs, radio buttons, checkboxes for consistent UX.
    
    Args:
        widget: Qt widget to apply hand cursor to (QPushButton, QRadioButton, etc.)
    
    Usage:
        button = QPushButton("Click Me")
        set_hand_cursor(button)
    """
    from PyQt5.QtCore import Qt
    widget.setCursor(Qt.PointingHandCursor)


def apply_hand_cursor_to_buttons(parent_widget):
    """
    Apply hand cursor to clickable widgets in a widget hierarchy.
    
    Successfully applies to:
    ✓ QToolButton (toolbar buttons)
    ✓ QPushButton (when set during creation)
    ✓ QRadioButton
    ✓ QCheckBox
    ✓ QComboBox  
    ✓ QTabBar
    ✓ QSpinBox (entire widget including up/down buttons)
    ✓ QDoubleSpinBox (entire widget including up/down buttons)
    
    Note: Spinbox sub-controls (up/down buttons) are not separate widgets,
    so the cursor applies to the entire spinbox including the text field.
    
    Args:
        parent_widget: Parent widget (QDialog, QMainWindow, etc.)
    
    Usage:
        dialog = MyDialog()
        apply_hand_cursor_to_buttons(dialog)
        dialog.show()
    """
    from PyQt5.QtWidgets import (
        QToolButton, QPushButton, QRadioButton, 
        QCheckBox, QComboBox, QTabBar, QSpinBox, QDoubleSpinBox
    )
    from PyQt5.QtCore import Qt
    
    # Apply hand cursor to widgets
    for tool_btn in parent_widget.findChildren(QToolButton):
        tool_btn.setCursor(Qt.PointingHandCursor)
    
    for push_btn in parent_widget.findChildren(QPushButton):
        push_btn.setCursor(Qt.PointingHandCursor)
    
    for radio in parent_widget.findChildren(QRadioButton):
        radio.setCursor(Qt.PointingHandCursor)
    
    for checkbox in parent_widget.findChildren(QCheckBox):
        checkbox.setCursor(Qt.PointingHandCursor)
    
    for combo in parent_widget.findChildren(QComboBox):
        combo.setCursor(Qt.PointingHandCursor)
    
    for tab in parent_widget.findChildren(QTabBar):
        tab.setCursor(Qt.PointingHandCursor)
    
    for spinbox in parent_widget.findChildren(QSpinBox):
        spinbox.setCursor(Qt.PointingHandCursor)
    
    for doublespinbox in parent_widget.findChildren(QDoubleSpinBox):
        doublespinbox.setCursor(Qt.PointingHandCursor)


# =============================================================================
# EXIT CONDITION STYLES (Sprint 1.8 - Phase 6)
# =============================================================================

def get_and_button_stylesheet() -> str:
    """
    Get stylesheet for "Add as AND (Required)" button (cyan/teal theme).
    Used in block search panel for required signal logic.
    
    Returns:
        Button stylesheet string with cyan/teal theme
    """
    return """
        QPushButton {
            background-color: #00D9FF;
            color: #0F1419;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 10pt;
        }
        QPushButton:hover {
            background-color: #0A7EA4;
        }
        QPushButton:disabled {
            background-color: #374151;
            color: #94A3B8;
        }
    """


def get_or_button_stylesheet() -> str:
    """
    Get stylesheet for "Add as OR (Optional)" button (green theme).
    Used in block search panel for optional signal logic.
    
    Returns:
        Button stylesheet string with green theme
    """
    return """
        QPushButton {
            background-color: #10B981;
            color: white;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 10pt;
        }
        QPushButton:hover {
            background-color: #059669;
        }
        QPushButton:disabled {
            background-color: #374151;
            color: #94A3B8;
        }
    """


def get_exit_button_stylesheet() -> str:
    """
    Get stylesheet for "Add as Exit" button (red theme).
    Sprint 1.8 Task 1.8.43
    
    Returns:
        Button stylesheet string with red/danger theme
    """
    return f"""
        QPushButton {{
            background-color: {COLORS['button_danger']};
            color: white;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            font-size: 10pt;
        }}
        QPushButton:hover {{
            background-color: {COLORS['button_danger_hover']};
        }}
        QPushButton:pressed {{
            background-color: #8B3333;
        }}
        QPushButton:disabled {{
            background-color: #374151;
            color: #94A3B8;
        }}
    """


def get_exit_dialog_stylesheet() -> str:
    """
    Get stylesheet for Exit Condition Dialog.
    Sprint 1.8 Task 1.8.44
    
    Returns:
        Dialog stylesheet string with dark theme and exit condition styling
    """
    return f"""
        QDialog {{
            background-color: {COLORS['bg_dark']};
            color: {COLORS['text_primary']};
            min-width: 800px;
            max-width: 800px;
        }}
        QLabel {{
            color: {COLORS['text_primary']};
            background: transparent;
        }}
        QGroupBox {{
            background-color: {COLORS['bg_medium']};
            border: 1px solid {COLORS['border']};
            border-radius: 8px;
            margin-top: 20px;
            padding-top: 35px;
            color: {COLORS['text_primary']};
            font-weight: bold;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 5px;
            color: {COLORS['text_muted']};
            font-size: 11pt;
            font-weight: bold;
        }}
        QComboBox {{
            background-color: {COLORS['bg_input']};
            border: 1px solid {COLORS['border']};
            border-radius: 6px;
            padding: 6px 10px;
            color: {COLORS['text_primary']};
        }}
        QComboBox:hover {{
            border-color: {COLORS['border_focus']};
        }}
        QComboBox::drop-down {{
            border: none;
            background: transparent;
        }}
        QComboBox QAbstractItemView {{
            background-color: {COLORS['bg_input']};
            border: none;
            selection-background-color: {COLORS['border_focus']};
            alternate-background-color: {COLORS['bg_input']};
            color: {COLORS['text_primary']};
            outline: none;
            show-decoration-selected: 0;
            gridline-color: {COLORS['bg_input']};
            spacing: 0px;
        }}
        QComboBox QAbstractItemView::item {{
            background-color: {COLORS['bg_input']};
            color: {COLORS['text_primary']};
            padding: 6px 8px;
            margin: 0px;
            border: none;
            spacing: 0px;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {COLORS['border_focus']};
            color: #FFFFFF;
            border: 0px solid transparent;
            margin: 0px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {COLORS['button_secondary']};
            border: 0px solid transparent;
            margin: 0px;
        }}
    """


def get_exit_tree_item_style() -> str:
    """
    Get stylesheet for exit condition tree items.
    Sprint 1.8 Task 1.8.45
    
    Returns:
        CSS style string for exit condition tree items (red theme, bold)
    """
    return f"color: {COLORS['aqua']}; font-weight: 100;"


# Backward compatibility constants (can be used directly)
EXIT_BUTTON_STYLE = get_exit_button_stylesheet()
EXIT_DIALOG_STYLE = get_exit_dialog_stylesheet()
EXIT_TREE_ITEM_STYLE = get_exit_tree_item_style()


# =============================================================================
# EXIT CONDITION BROWSER STYLES (Sprint 1.9.1)
# =============================================================================

def get_exit_binding_badge_style(binding_level: str) -> str:
    """
    Get badge style for exit condition binding levels.
    Sprint 1.9.1 Task 1.9.1.2
    
    Args:
        binding_level: 'STRATEGY', 'BLOCK', or 'SIGNAL'
    
    Returns:
        CSS style string with color-coded background
    """
    colors = {
        'STRATEGY': COLORS['exit_strategy_level'],  # Blue
        'BLOCK': COLORS['exit_block_level'],         # Green
        'SIGNAL': COLORS['exit_signal_level']        # Yellow
    }
    color = colors.get(binding_level, COLORS['exit_strategy_level'])
    
    return f"background-color: {color}; color: white; padding: 2px 6px; border-radius: 3px; font-weight: bold;"


def get_cumulative_exit_color(cumulative_percentage: float) -> str:
    """
    Get color for cumulative exit percentage badge.
    Sprint 1.9.1 Task 1.9.1.5
    
    Color coding:
    - 0%: Gray (TP-only)
    - 1-99%: Blue (Hybrid)
    - 100%: Green (Full exit)
    - 101-500%: Yellow (Multiple opportunities)
    - >500%: Orange (High redundancy - review recommended)
    
    Args:
        cumulative_percentage: Total exit percentage (0-1000+)
    
    Returns:
        Hex color string
    """
    if cumulative_percentage == 0:
        return COLORS['exit_cumulative_tp_only']      # Gray
    elif cumulative_percentage < 100:
        return COLORS['exit_cumulative_hybrid']       # Blue
    elif cumulative_percentage == 100:
        return COLORS['exit_cumulative_full']         # Green
    elif cumulative_percentage <= 500:
        return COLORS['exit_cumulative_multiple']     # Yellow
    else:
        return COLORS['exit_cumulative_high']         # Orange


def get_auto_fix_button_style() -> str:
    """
    Get stylesheet for auto-fix action buttons.
    Sprint 1.9.2 Task 1.9.2.6
    
    Institutional-grade styling for one-click auto-fix buttons.
    Uses success color (green) to indicate safe, automated action.
    
    Returns:
        Button stylesheet string with success theme
    """
    return f'''
        QPushButton {{
            background-color: {COLORS['success']};
            color: white;
            font-weight: bold;
            padding: 6px 12px;
            border-radius: 4px;
            min-width: 90px;
            font-size: 9pt;
            border: none;
        }}
        QPushButton:hover {{
            background-color: #059669;
            border: 1px solid #10B981;
        }}
        QPushButton:pressed {{
            background-color: #047857;
        }}
        QPushButton:disabled {{
            background-color: #555555;
            color: #888888;
        }}
    '''


def get_exit_icon() -> str:
    """
    Get exit condition icon.
    Sprint 1.9.1 Task 1.9.1.1
    
    Returns:
        Exit icon emoji
    """
    return "🚪"


def get_recheck_depth_color(depth: int) -> str:
    """
    Get color for RECHECK chain depth visualization.
    Sprint 1.9.1 Task 1.9.1.4
    
    Color coding:
    - Depth 1: Green
    - Depth 2: Yellow
    - Depth 3+: Red
    
    Args:
        depth: RECHECK nesting depth (1, 2, 3+)
    
    Returns:
        Hex color string
    """
    if depth == 1:
        return COLORS['exit_block_level']      # Green
    elif depth == 2:
        return COLORS['exit_signal_level']     # Yellow
    else:
        return COLORS['exit_cumulative_high']  # Red


def format_block_name(block_name: str) -> str:
    """
    Format block name for UI display with proper title casing.
    
    Rules:
    - Replace underscores with spaces
    - Capitalize first letter of each word
    - Keep "and" lowercase
    
    Examples:
        "cup_and_handle" → "Cup and Handle"
        "inverse_head_and_shoulders" → "Inverse Head and Shoulders"
        "falling_wedge" → "Falling Wedge"
    
    Args:
        block_name: Raw block name with underscores
        
    Returns:
        Formatted block name for display
    """
    # Replace underscores with spaces
    formatted = block_name.replace('_', ' ')
    
    # Split into words and capitalize each
    words = formatted.split()
    capitalized_words = []
    
    for word in words:
        # Keep "and" lowercase, capitalize everything else
        if word.lower() == 'and':
            capitalized_words.append('and')
        else:
            capitalized_words.append(word.capitalize())
    
    return ' '.join(capitalized_words)
