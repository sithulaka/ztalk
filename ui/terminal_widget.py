import customtkinter as ctk
import tkinter as tk
from typing import Optional, Dict, List, Callable

class TerminalWidget(ctk.CTkFrame):
    """A widget for displaying and entering commands"""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create a text display area with scrollbar
        self.display_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.display_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.display_frame.grid_columnconfigure(0, weight=1)
        self.display_frame.grid_rowconfigure(0, weight=1)
        
        # Text display with a scrollbar
        self.display = ctk.CTkTextbox(self.display_frame, wrap="word", height=300)
        self.display.grid(row=0, column=0, sticky="nsew")
        self.display.configure(state="disabled")
        
        # Scrollbar
        scrollbar = ctk.CTkScrollbar(self.display_frame, command=self.display.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.display.configure(yscrollcommand=scrollbar.set)
        
        # Command input area
        self.input_frame = ctk.CTkFrame(self, height=40, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=(0, 5))
        self.input_frame.grid_columnconfigure(1, weight=1)
        
        # Prompt label
        self.prompt = ctk.CTkLabel(self.input_frame, text="$ ", width=20, anchor="e")
        self.prompt.grid(row=0, column=0, sticky="w")
        
        # Command entry
        self.command_entry = ctk.CTkEntry(self.input_frame, height=30)
        self.command_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        self.command_entry.bind("<Return>", self.handle_command)
        self.command_entry.bind("<Up>", self.history_up)
        self.command_entry.bind("<Down>", self.history_down)
        
        # Command history
        self.command_history = []
        self.history_index = -1
        
        # Configure text color tags
        self._setup_text_tags()
        
    def _setup_text_tags(self):
        """Set up text color configurations"""
        try:
            text_widget = self.display._textbox
            text_widget.tag_configure("error", foreground="#F44336")  # Red
            text_widget.tag_configure("success", foreground="#4CAF50")  # Green
            text_widget.tag_configure("info", foreground="#2196F3")  # Blue
            text_widget.tag_configure("warning", foreground="#FF9800")  # Orange
            text_widget.tag_configure("command", foreground="#E1BEE7")  # Light purple
        except (AttributeError, tk.TclError) as e:
            print(f"Warning: Could not configure text tags: {e}")
    
    def append_text(self, text: str, tag: Optional[str] = None):
        """Append text to the display with optional tag for color"""
        self.display.configure(state="normal")
        if tag:
            self.display.insert("end", text, tag)
        else:
            self.display.insert("end", text)
        self.display.configure(state="disabled")
        self.display.see("end")
    
    def clear_display(self):
        """Clear the display"""
        self.display.configure(state="normal")
        self.display.delete("1.0", "end")
        self.display.configure(state="disabled")
    
    def handle_command(self, event=None):
        """Handle command entry"""
        command = self.command_entry.get().strip()
        if not command:
            return
        
        # Add to display with command color
        self.append_text(f"$ {command}\n", "command")
        
        # Add to history
        self.command_history.append(command)
        self.history_index = -1
        
        # Clear entry
        self.command_entry.delete(0, "end")
        
        # Pass command to handler if defined
        if hasattr(self, "command_handler") and self.command_handler:
            self.command_handler(command)
    
    def set_command_handler(self, handler: Callable[[str], None]):
        """Set a callback function to handle commands"""
        self.command_handler = handler
    
    def history_up(self, event=None):
        """Navigate up through command history"""
        if not self.command_history:
            return "break"
            
        if self.history_index == -1:
            self.history_index = len(self.command_history) - 1
        elif self.history_index > 0:
            self.history_index -= 1
            
        self.command_entry.delete(0, "end")
        self.command_entry.insert(0, self.command_history[self.history_index])
        return "break"
    
    def history_down(self, event=None):
        """Navigate down through command history"""
        if not self.command_history or self.history_index == -1:
            return "break"
            
        if self.history_index < len(self.command_history) - 1:
            self.history_index += 1
            self.command_entry.delete(0, "end")
            self.command_entry.insert(0, self.command_history[self.history_index])
        else:
            self.history_index = -1
            self.command_entry.delete(0, "end")
            
        return "break"