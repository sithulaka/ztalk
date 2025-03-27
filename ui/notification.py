import customtkinter as ctk
import tkinter as tk
from typing import Optional, List, Dict, Any
import time
import threading
import weakref  # Import weakref to prevent circular references

class Notification(ctk.CTkFrame):
    """
    A modern notification widget that appears at the top-right of the screen
    and automatically disappears after a set duration.
    
    Types:
    - success: green
    - error: red
    - warning: orange
    - info: blue
    """
    
    # Class variable to track active notifications - use weakrefs to prevent circular references
    _active_notifications = []
    _positions: Dict[int, Dict[str, Any]] = {}
    
    def __init__(
        self, 
        master: Optional[ctk.CTk] = None,
        title: str = "",
        message: str = "",
        duration: int = 3000,  # ms 
        notification_type: str = "info",
        width: int = 300,
        corner_radius: int = 10,
        **kwargs
    ):
        # Store parameters
        self.title = title
        self.message = message
        self.duration = duration
        self.notification_type = notification_type.lower()
        self.notification_width = width
        
        # Define colors for different notification types
        self.colors = {
            "success": {
                "bg": "#43A047",
                "fg": "#FFFFFF",
                "icon": "✓"
            },
            "error": {
                "bg": "#E53935",
                "fg": "#FFFFFF",
                "icon": "✕"
            },
            "warning": {
                "bg": "#FF8C00",
                "fg": "#FFFFFF", 
                "icon": "⚠"
            },
            "info": {
                "bg": "#2196F3",
                "fg": "#FFFFFF",
                "icon": "ℹ"
            }
        }
        
        # Use default type if the specified type is not found
        if self.notification_type not in self.colors:
            self.notification_type = "info"
        
        # Create toplevel window for the notification
        self.window = ctk.CTkToplevel(master)
        self.window.withdraw()  # Hide until we position it
        self.window.overrideredirect(True)  # Removes window decorations
        
        # Make the window float on top
        self.window.attributes("-topmost", True)
        
        # Create frame in the window
        super().__init__(
            self.window,
            width=width,
            corner_radius=corner_radius,
            fg_color=self.colors[self.notification_type]["bg"],
            **kwargs
        )
        self.pack(fill="both", expand=True)
        
        # Layout for the notification content
        self.grid_columnconfigure(1, weight=1)
        
        # Icon
        self.icon_label = ctk.CTkLabel(
            self,
            text=self.colors[self.notification_type]["icon"],
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.colors[self.notification_type]["fg"],
            width=30
        )
        self.icon_label.grid(row=0, column=0, rowspan=2, padx=(10, 5), pady=10)
        
        # Title
        if title:
            self.title_label = ctk.CTkLabel(
                self,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=self.colors[self.notification_type]["fg"],
                anchor="w"
            )
            self.title_label.grid(row=0, column=1, padx=(0, 10), pady=(10, 0), sticky="w")
        
        # Message
        self.message_label = ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont(size=12),
            text_color=self.colors[self.notification_type]["fg"],
            anchor="w",
            justify="left",
            wraplength=width - 80  # Account for padding and icon
        )
        self.message_label.grid(
            row=1 if title else 0, 
            column=1, 
            padx=(0, 10), 
            pady=(0 if title else 10, 10), 
            sticky="w"
        )
        
        # Close button
        self.close_btn = ctk.CTkButton(
            self,
            text="×",
            font=ctk.CTkFont(size=14, weight="bold"),
            width=20,
            height=20,
            fg_color="transparent",
            hover_color=self.adjust_color(self.colors[self.notification_type]["bg"], -20),
            text_color=self.colors[self.notification_type]["fg"],
            command=self.destroy
        )
        self.close_btn.grid(row=0, column=2, padx=(0, 5), pady=(5, 0), sticky="ne")
        
        # Add to active notifications list and position it
        type(self)._active_notifications.append(weakref.ref(self))
        
        # Show the notification with animation
        self.show()
        
    def show(self):
        """Show the notification with animation"""
        # First calculate the position based on existing notifications
        self.position_notification()
        
        # Then make the window visible
        if hasattr(self, "window") and self.window:
            try:
                self.window.deiconify()
                
                # Start timer for auto-removal
                if self.duration > 0:
                    self.window.after(self.duration, self.start_fade_out)
            except (tk.TclError, AttributeError) as e:
                print(f"Error showing notification: {e}")
    
    def position_notification(self):
        """Position the notification on screen"""
        # Check if window still exists
        if not hasattr(self, "window") or self.window is None:
            return
            
        try:
            # Calculate notification height
            self.window.update_idletasks()
            width = self.notification_width
            height = self.winfo_reqheight()
            
            # Get screen dimensions
            screen_width = self.window.winfo_screenwidth()
            screen_height = self.window.winfo_screenheight()
            
            # Calculate position (top-right by default)
            x = screen_width - width - 20  # 20px padding from right edge
            
            # Find the next available vertical position
            index = len(type(self)._active_notifications) - 1
            pos_y = 20  # Start 20px from top
            
            # Check existing notifications and stack below them
            for i, notif_ref in enumerate(type(self)._active_notifications[:-1]):
                # Get the actual notification from the weakref
                notif = notif_ref()
                if notif is None:
                    continue
                    
                if i in type(self)._positions:
                    pos_y = type(self)._positions[i]["y"] + type(self)._positions[i]["height"] + 10
            
            # Store this notification's position
            type(self)._positions[index] = {
                "x": x,
                "y": pos_y,
                "width": width,
                "height": height
            }
            
            # Set the window position
            self.window.geometry(f"{width}x{height}+{x}+{pos_y}")
        except (tk.TclError, AttributeError) as e:
            print(f"Error positioning notification: {e}")
    
    def start_fade_out(self):
        """Start the fade-out animation"""
        # Check if window still exists
        if hasattr(self, "window") and self.window:
            try:
                self.fade_out()
            except Exception as e:
                print(f"Error starting fade out: {e}")
                self.destroy()
    
    def fade_out(self, current_alpha=1.0):
        """Gradually fade out the notification"""
        # Safety check
        if not hasattr(self, "window") or self.window is None:
            return
            
        if current_alpha <= 0.1:
            # Just destroy directly instead of recursive call
            self.destroy()
            return
        
        try:
            # Reduce alpha
            next_alpha = current_alpha - 0.1
            
            # Set transparency for the window
            self.window.attributes("-alpha", next_alpha)
            
            # Don't use lambda for next step to avoid closure issues
            self.window.after(50, lambda: self._fade_next_step(next_alpha))
        except (tk.TclError, AttributeError, RuntimeError) as e:
            # Window might be destroyed already
            print(f"Error in fade_out: {e}")
            self.destroy()
    
    def _fade_next_step(self, alpha):
        """Separate method to continue fading to avoid lambda closures"""
        # Safety check for recursive calls
        if hasattr(self, "window") and self.window:
            self.fade_out(alpha)
    
    def destroy(self):
        """Destroy the notification"""
        # First remove self from active notifications list to prevent circular reference
        for i, notif_ref in enumerate(type(self)._active_notifications):
            notif = notif_ref()
            if notif is self:
                type(self)._active_notifications.pop(i)
                # Remove from positions dictionary
                if i in type(self)._positions:
                    del type(self)._positions[i]
                break
        
        # Prevent recursive calls by checking if we're already destroying
        if not hasattr(self, "_destroying") or not self._destroying:
            self._destroying = True
            
            # Reposition remaining notifications
            self.reposition_notifications()
            
            # Destroy the window - wrap in try/except to handle cases where window is already destroyed
            try:
                if hasattr(self, 'window') and self.window:
                    # Just use window.destroy() directly to avoid recursion
                    window = self.window
                    self.window = None  # Remove reference first
                    window.destroy()
            except (tk.TclError, RuntimeError, RecursionError) as e:
                print(f"Error during notification destruction: {e}")
            
            # Clear references
            self.close_btn = None
            self.icon_label = None
            if hasattr(self, "title_label"):
                self.title_label = None
            self.message_label = None
        
        # Don't call super().destroy() as it can cause recursion
    
    def reposition_notifications(self):
        """Reposition remaining notifications after one is closed"""
        # Create a new positions dictionary
        new_positions = {}
        
        # Start from the top
        pos_y = 20
        
        # Reposition each notification
        for i, notif_ref in enumerate(type(self)._active_notifications):
            # Get the notification object from the weakref
            notif = notif_ref()
            
            # Skip if the notification has been garbage collected
            if notif is None:
                continue
                
            if i in type(self)._positions:
                # Keep x and size, update y
                new_positions[i] = type(self)._positions[i].copy()
                new_positions[i]["y"] = pos_y
                
                # Update window position
                if hasattr(notif, 'window') and notif.window:
                    try:
                        notif.window.geometry(
                            f"{new_positions[i]['width']}x{new_positions[i]['height']}+"
                            f"{new_positions[i]['x']}+{new_positions[i]['y']}"
                        )
                    except tk.TclError:
                        continue  # Skip if window has been destroyed
                
                # Update next position
                pos_y = new_positions[i]["y"] + new_positions[i]["height"] + 10
        
        # Update positions dictionary
        type(self)._positions = new_positions
    
    def adjust_color(self, hex_color, amount):
        """Adjust color brightness"""
        # Convert hex to RGB
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        
        # Adjust brightness
        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))
        
        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @classmethod
    def success(cls, master=None, title="Success", message="", duration=3000):
        """Show a success notification"""
        return cls(master, title, message, duration=duration, notification_type="success")
    
    @classmethod
    def error(cls, master=None, title="Error", message="", duration=3000):
        """Show an error notification"""
        return cls(master, title, message, duration=duration, notification_type="error")
    
    @classmethod
    def warning(cls, master=None, title="Warning", message="", duration=3000):
        """Show a warning notification"""
        return cls(master, title, message, duration=duration, notification_type="warning")
    
    @classmethod
    def info(cls, master=None, title="Information", message="", duration=3000):
        """Show an info notification"""
        return cls(master, title, message, duration=duration, notification_type="info") 