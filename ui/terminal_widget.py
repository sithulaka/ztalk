"""
Terminal Widget for ZTalk

Implements a terminal emulator widget for SSH connections.
"""

import os
import sys
import time
import threading
import logging
from typing import Optional, Callable, List, Dict, Any, Tuple

# Use prompt_toolkit for the terminal UI
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import HSplit, VSplit, Window, WindowAlign, Float, FloatContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import TextArea, Frame, Box, Label
from prompt_toolkit.filters import Condition
from prompt_toolkit.input.defaults import create_input
from prompt_toolkit.output.defaults import create_output

# Configure logging
logger = logging.getLogger(__name__)

class TerminalWidget:
    """
    A terminal emulator widget using prompt_toolkit.
    Can be used for SSH sessions or local shell.
    """
    
    def __init__(self,
                name: str = "Terminal",
                max_history_size: int = 10000,
                on_input: Optional[Callable[[str], None]] = None,
                on_exit: Optional[Callable[[], None]] = None):
        """
        Initialize a new terminal widget.
        
        Args:
            name: Display name for the terminal
            max_history_size: Maximum number of lines to keep in the terminal
            on_input: Callback for when user enters input
            on_exit: Callback for when user exits the terminal
        """
        self.name = name
        self.max_history_size = max_history_size
        self.on_input_callback = on_input
        self.on_exit_callback = on_exit
        
        # Terminal state
        self.connected = False
        self.history_lines: List[str] = []
        self.pending_output = ""
        self.ansi_color_map = {
            # Regular colors
            '30': 'black',
            '31': 'red',
            '32': 'green',
            '33': 'yellow',
            '34': 'blue',
            '35': 'magenta',
            '36': 'cyan',
            '37': 'white',
            # Bright colors
            '90': 'gray',
            '91': 'bright_red',
            '92': 'bright_green',
            '93': 'bright_yellow',
            '94': 'bright_blue',
            '95': 'bright_magenta',
            '96': 'bright_cyan',
            '97': 'bright_white',
        }
        
        # UI components
        self.content = FormattedTextControl(
            self._get_formatted_history,
            focusable=False
        )
        
        self.window = Window(
            content=self.content,
            dont_extend_height=False
        )
        
        self.input_field = TextArea(
            prompt="$ ",
            multiline=False,
            wrap_lines=False,
            height=1,
            style="class:input-field",
            focus_on_click=True,
            accept_handler=self._accept_input
        )
        
        self.status_bar = Label(
            text=HTML(f"<b>{self.name}</b> | Press Ctrl+D to exit"),
            style="class:status-bar",
            align=WindowAlign.CENTER
        )
        
        # Create the layout
        self.container = HSplit([
            Frame(
                title=self.name,
                body=self.window
            ),
            self.input_field,
            self.status_bar
        ])
        
        # Key bindings
        self.kb = KeyBindings()
        
        @self.kb.add('c-d')
        def _(event):
            """Exit on Ctrl+D"""
            if self.on_exit_callback:
                self.on_exit_callback()
            event.app.exit()
            
        # Style
        self.style = Style.from_dict({
            'frame.border': '#888888',
            'status-bar': 'bg:#333333 #ffffff',
            'input-field': 'bg:#000000 #ffffff',
            'input-field.prompt': 'bold',
            
            # Basic colors for terminal output
            'black': '#000000',
            'red': '#ff0000',
            'green': '#00ff00',
            'yellow': '#ffff00',
            'blue': '#0000ff',
            'magenta': '#ff00ff',
            'cyan': '#00ffff',
            'white': '#ffffff',
            
            # Bright colors
            'gray': '#888888',
            'bright_red': '#ff8888',
            'bright_green': '#88ff88',
            'bright_yellow': '#ffff88',
            'bright_blue': '#8888ff',
            'bright_magenta': '#ff88ff',
            'bright_cyan': '#88ffff',
            'bright_white': '#ffffff',
        })
        
        # Application
        self.application = Application(
            layout=Layout(self.container),
            key_bindings=self.kb,
            style=self.style,
            full_screen=True,
            mouse_support=True
        )
        
        # Make sure the input field has focus by default
        self.application.layout.focus(self.input_field)
    
    def run(self):
        """Run the terminal application"""
        logger.info(f"Starting terminal widget: {self.name}")
        try:
            self.application.run()
        except Exception as e:
            logger.error(f"Error running terminal: {e}")
        finally:
            logger.info(f"Terminal widget closed: {self.name}")
    
    def add_output(self, text: str):
        """
        Add output to the terminal.
        This method is thread-safe and can be called from any thread.
        """
        # Split text into lines
        lines = text.split('\n')
        if self.pending_output:
            lines[0] = self.pending_output + lines[0]
            self.pending_output = ""
            
        # If the last line doesn't end with a newline,
        # keep it as pending output
        if text and not text.endswith('\n'):
            self.pending_output = lines.pop()
            
        # Add new lines to history
        self.history_lines.extend(lines)
        
        # Trim history if needed
        if len(self.history_lines) > self.max_history_size:
            self.history_lines = self.history_lines[-self.max_history_size:]
            
        # Force redraw
        try:
            self.content.invalidate()
        except Exception:
            # The application might not be running yet
            pass
    
    def set_status(self, text: str):
        """Set the status bar text"""
        self.status_bar.text = HTML(text)
        try:
            # Invalidate to force redraw
            self.status_bar.invalidate()
        except Exception:
            # The application might not be running yet
            pass
    
    def set_connected(self, connected: bool):
        """Set the connected state"""
        self.connected = connected
        if connected:
            self.set_status(HTML(f"<b>{self.name}</b> | Connected | Press Ctrl+D to exit"))
        else:
            self.set_status(HTML(f"<b>{self.name}</b> | Disconnected | Press Ctrl+D to exit"))
    
    def clear(self):
        """Clear the terminal"""
        self.history_lines = []
        self.pending_output = ""
        try:
            self.content.invalidate()
        except Exception:
            # The application might not be running yet
            pass
            
    # Private methods
    
    def _accept_input(self, buffer):
        """
        Handle user input from the input field.
        This is called when the user presses Enter.
        """
        text = buffer.text
        
        # Echo input to the terminal
        self.add_output(f"$ {text}\n")
        
        # Call the input callback
        if self.on_input_callback:
            self.on_input_callback(text)
            
        # Don't clear the prompt, as it will be overwritten when the result arrives
        return False
    
    def _get_formatted_history(self):
        """
        Convert the terminal history to formatted text.
        This handles ANSI escape sequences for colors.
        """
        formatted_text = []
        
        for line in self.history_lines:
            formatted_text.extend(self._process_ansi_escape_sequences(line))
            formatted_text.append(('', '\n'))
            
        if self.pending_output:
            formatted_text.extend(self._process_ansi_escape_sequences(self.pending_output))
            
        return formatted_text
            
    def _process_ansi_escape_sequences(self, text):
        """Process ANSI escape sequences for colors"""
        result = []
        
        # We'll handle simple ANSI codes (like \x1b[31m for red text)
        parts = text.split('\x1b[')
        
        if len(parts) == 1:
            # No ANSI codes
            return [('', text)]
            
        # First part before any ANSI codes
        if parts[0]:
            result.append(('', parts[0]))
            
        for i, part in enumerate(parts[1:], 1):
            if not part:
                continue
                
            # Split at first 'm' to get the code
            if 'm' in part:
                code, text_part = part.split('m', 1)
                
                # Reset
                if code == '0':
                    color = ''
                else:
                    # Handle one or more color codes separated by ;
                    codes = code.split(';')
                    color = None
                    
                    for c in codes:
                        if c in self.ansi_color_map:
                            color = f"class:{self.ansi_color_map[c]}"
                            break
                            
                    if color is None:
                        color = ''
                
                result.append((color, text_part))
            else:
                # If no 'm', just append as is
                result.append(('', part))
                
        return result 