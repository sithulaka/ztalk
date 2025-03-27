"""
ZTalk UI Configuration

This module defines global UI constants including color schemes, font settings,
and other design-related configuration.
"""
import platform  # Import platform to determine OS for font settings

# Color schemes
DARK_THEME = {
    # Background colors (from darkest to lightest)
    "bg_darkest": "#0E1621",    # Main background
    "bg_dark": "#17212B",       # Container background
    "bg_medium": "#1E2933",     # Sidebar background
    "bg_light": "#242F3D",      # Input fields, buttons
    
    # Text colors
    "text_light": "#FFFFFF",    # Primary text
    "text_gray": "#8696A0",     # Secondary text
    "text_disabled": "#586975", # Disabled text
    
    # Accent colors
    "accent_primary": "#3E92CC",    # Primary brand color
    "accent_hover": "#2A7AB0",      # Hover state
    "accent_secondary": "#5CB85C",  # Secondary actions
    
    # Status colors
    "success": "#43A047",   # Success messages/indicators
    "error": "#E53935",     # Error messages/indicators
    "warning": "#FF8C00",   # Warning messages/indicators
    "info": "#2196F3",      # Info messages/indicators
    
    # Structural elements
    "separator": "#262D31", # Dividers, separators
    "border": "#324652",    # Borders
    
    # Message colors
    "message_sent": "#176B87",      # Sent message bubbles
    "message_received": "#242F3D",  # Received message bubbles
    "message_system": "#3B4252",    # System message background
}

LIGHT_THEME = {
    # Background colors (from lightest to darkest)
    "bg_darkest": "#F0F2F5",    # Main background
    "bg_dark": "#FFFFFF",       # Container background
    "bg_medium": "#F5F5F5",     # Sidebar background
    "bg_light": "#E9EDEF",      # Input fields, buttons
    
    # Text colors
    "text_light": "#1E1E1E",    # Primary text
    "text_gray": "#667781",     # Secondary text
    "text_disabled": "#A0A0A0", # Disabled text
    
    # Accent colors
    "accent_primary": "#2D88FF",    # Primary brand color
    "accent_hover": "#1A73E8",      # Hover state
    "accent_secondary": "#4CAF50",  # Secondary actions
    
    # Status colors
    "success": "#43A047",   # Success messages/indicators
    "error": "#E53935",     # Error messages/indicators
    "warning": "#FF9800",   # Warning messages/indicators
    "info": "#2196F3",      # Info messages/indicators
    
    # Structural elements
    "separator": "#E0E0E0", # Dividers, separators
    "border": "#D1D7DB",    # Borders
    
    # Message colors
    "message_sent": "#DCF8C6",      # Sent message bubbles
    "message_received": "#FFFFFF",  # Received message bubbles
    "message_system": "#F5F5F5",    # System message background
}

# Font configurations
FONTS = {
    "regular": {
        "family": "Segoe UI" if platform.system() == "Windows" else "Helvetica",
        "size": 12,
        "weight": "normal"
    },
    "bold": {
        "family": "Segoe UI" if platform.system() == "Windows" else "Helvetica",
        "size": 12,
        "weight": "bold"
    },
    "large": {
        "family": "Segoe UI" if platform.system() == "Windows" else "Helvetica",
        "size": 16,
        "weight": "normal"
    },
    "large_bold": {
        "family": "Segoe UI" if platform.system() == "Windows" else "Helvetica",
        "size": 16,
        "weight": "bold"
    },
    "small": {
        "family": "Segoe UI" if platform.system() == "Windows" else "Helvetica",
        "size": 10,
        "weight": "normal"
    },
    "monospace": {
        "family": "Consolas" if platform.system() == "Windows" else "Courier",
        "size": 12,
        "weight": "normal"
    }
}

# UI sizing and spacing
DIMENSIONS = {
    "sidebar_width": 280,
    "chat_input_height": 60,
    "message_padding": 10,
    "button_height": 36,
    "input_height": 36,
    "corner_radius": 8,
    "spacing_small": 5,
    "spacing_medium": 10,
    "spacing_large": 20
}

# Animation durations (in milliseconds)
ANIMATIONS = {
    "transition_fast": 100,
    "transition_normal": 200,
    "transition_slow": 300,
    "notification_display": 3000,
    "typing_indicator": 500
}

# Default application settings
DEFAULT_SETTINGS = {
    "theme": "dark",
    "notifications_enabled": True,
    "sound_enabled": True,
    "auto_reconnect": True,
    "message_preview": True,
    "save_chat_history": True
}

# Get the current theme based on settings
def get_current_theme(theme_name="dark"):
    """Return the color scheme for the specified theme"""
    return DARK_THEME if theme_name.lower() == "dark" else LIGHT_THEME 