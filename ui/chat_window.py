import customtkinter as ctk
import tkinter as tk
from datetime import datetime
from typing import Callable, Optional, Dict, List
import os
import platform
import sys
import threading
import gc  # For garbage collection, used to find app instances
import ipaddress  # For DHCP network validation
from PIL import Image, ImageTk
from .ssh_client import SSHClient
from .notification import Notification

# Import CTkMessagebox for confirmation dialogs
try:
    from CTkMessagebox import CTkMessagebox
except ImportError:
    # Fallback to a basic implementation if CTkMessagebox is not available
    class CTkMessagebox:
        def __init__(self, title, message, icon, option_1, option_2):
            self.title = title
            self.message = message
            self.response = None
            
            # Create a simple dialog
            self.dialog = ctk.CTkToplevel()
            self.dialog.title(title)
            self.dialog.geometry("400x200")
            self.dialog.resizable(False, False)
            
            # Make it modal
            self.dialog.transient()
            self.dialog.grab_set()
            
            # Message
            message_label = ctk.CTkLabel(self.dialog, text=message, wraplength=350)
            message_label.pack(pady=(20, 30))
            
            # Buttons
            button_frame = ctk.CTkFrame(self.dialog, fg_color="transparent")
            button_frame.pack(fill="x", padx=20, pady=10)
            
            # Option 1 button (usually Cancel)
            cancel_btn = ctk.CTkButton(button_frame, text=option_1, command=lambda: self.set_response(option_1))
            cancel_btn.pack(side="left", padx=10, pady=10, fill="x", expand=True)
            
            # Option 2 button (usually OK/Apply)
            ok_btn = ctk.CTkButton(button_frame, text=option_2, command=lambda: self.set_response(option_2))
            ok_btn.pack(side="right", padx=10, pady=10, fill="x", expand=True)
            
        def set_response(self, response):
            self.response = response
            self.dialog.destroy()
            
        def get(self):
            # Wait for the dialog to close
            self.dialog.wait_window()
            return self.response

class ChatWindow(ctk.CTk):
    def __init__(self, username: str = None, send_private_msg: Callable = None, send_broadcast: Callable = None, get_peers: Callable = None, 
                network_manager=None, enable_dhcp: Callable = None, get_dhcp_status: Callable = None):
        super().__init__()

        # Store callbacks
        self.send_private_msg = send_private_msg
        self.send_broadcast = send_broadcast
        self.get_peers = get_peers
        self.username = username
        self.platform = platform.system()  # 'Windows', 'Darwin' (macOS), or 'Linux'
        self.network_manager = network_manager  # Store network manager for advanced features
        self.enable_dhcp = enable_dhcp  # Store DHCP enable/disable function
        self.get_dhcp_status = get_dhcp_status  # Store DHCP status retrieval function
        
        # SSH client window
        self.ssh_client = None
        
        # Track auto-refresh ID for cancellation
        self._auto_refresh_id = None
        
        # Selected user for private messages
        self.selected_user = None

        # Configure window
        self.title("ZTalk")
        self.geometry("1000x700")
        self.minsize(800, 600)
        
        # Set appearance and theme
        self.setup_appearance_options()
        
        # Set platform-specific icon if available
        self.set_platform_specifics()
        
        # If username is not provided, ask for it first
        if not self.username:
            self.ask_username()
        else:
            self.initialize_ui()

    def set_platform_specifics(self):
        """Set platform-specific configurations"""
        # You can add icons for each platform here
        icon_path = None
        try:
            if self.platform == "Windows":
                self.protocol("WM_DELETE_WINDOW", self.on_closing)
                # Windows-specific tweaks can be added here
                pass
            elif self.platform == "Darwin":  # macOS
                # macOS-specific tweaks
                ctk.set_appearance_mode("system")  # Use system appearance mode on macOS
                # Handle Command+Q and proper window closing
                self.createcommand('exit', self.on_closing)
            elif self.platform == "Linux":
                # Linux-specific tweaks
                self.protocol("WM_DELETE_WINDOW", self.on_closing)
                pass
        except Exception as e:
            print(f"Error setting platform specifics: {e}")

    def setup_appearance_options(self):
        """Configure appearance and theme with user options"""
        # Set default theme
        ctk.set_appearance_mode("dark")  # Options: "dark", "light", "system"
        ctk.set_default_color_theme("blue")
        
        # Add appearance mode selector to sidebar
        self.appearance_mode_options = ["Light", "Dark", "System"]
        self.appearance_mode_var = ctk.StringVar(value="Dark")
        
        # Add more modern theme options
        self.color_theme_options = ["Blue", "Dark Blue", "Green", "Purple", "Teal"]
        self.color_theme_var = ctk.StringVar(value="Blue")
        
        # Define custom colors for modern UI
        self.colors = {
            "sidebar_bg": "#1E2933",
            "main_bg": "#0E1621",
            "chat_bg": "#17212B", 
            "input_bg": "#242F3D",
            "accent": "#3E92CC",
            "accent_hover": "#2A7AB0",
            "text_light": "#FFFFFF",
            "text_gray": "#8696A0",
            "message_sent": "#176B87",
            "message_received": "#242F3D",
            "system_message": "#FF8C00",
            "error_message": "#E53935",
            "success_message": "#43A047",
            "separator": "#262D31"
        }
        
        # Apply custom colors
        self.configure(fg_color=self.colors["main_bg"])

    def setup_user_profile(self):
        """Setup user profile section in sidebar"""
        self.profile_frame = ctk.CTkFrame(self.sidebar, fg_color=self.colors["sidebar_bg"])
        self.profile_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        # Header with username and avatar
        header_frame = ctk.CTkFrame(self.profile_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10, 5))
        
        # User avatar placeholder with circular appearance
        avatar_frame = ctk.CTkFrame(header_frame, width=50, height=50, 
                                   corner_radius=25, fg_color=self.colors["accent"])
        avatar_frame.pack(side="left", padx=(10, 15))
        avatar_frame.pack_propagate(False)
        
        avatar_initial = ctk.CTkLabel(avatar_frame, text=self.username[0].upper(),
                                    font=ctk.CTkFont(size=22, weight="bold"),
                                    text_color=self.colors["text_light"])
        avatar_initial.place(relx=0.5, rely=0.5, anchor="center")
        
        # User information
        user_info = ctk.CTkFrame(header_frame, fg_color="transparent")
        user_info.pack(side="left", fill="both", expand=True)
        
        self.username_label = ctk.CTkLabel(user_info, text=self.username,
                                         font=ctk.CTkFont(size=16, weight="bold"),
                                         text_color=self.colors["text_light"])
        self.username_label.pack(anchor="w")
        
        # Status indicator with modern appearance
        status_frame = ctk.CTkFrame(user_info, fg_color="transparent", height=25)
        status_frame.pack(fill="x", anchor="w")
        
        self.status_indicator = ctk.CTkLabel(status_frame, text="●", 
                                           text_color="#4CAF50", 
                                           font=ctk.CTkFont(size=14))
        self.status_indicator.pack(side="left", padx=(0, 5))
        
        self.status_label = ctk.CTkLabel(status_frame, text="Online", 
                                       text_color=self.colors["text_gray"],
                                       font=ctk.CTkFont(size=12))
        self.status_label.pack(side="left")
        
        # Add a subtle separator
        separator = ctk.CTkFrame(self.profile_frame, height=1, fg_color=self.colors["separator"])
        separator.pack(fill="x", pady=(10, 0))

    def setup_users_list(self):
        """Setup the online users list section"""
        # Title with user count
        self.users_header_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.users_header_frame.grid(row=1, column=0, padx=10, pady=(20, 0), sticky="ew")
        
        self.users_label = ctk.CTkLabel(self.users_header_frame, text="Online Users", 
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       text_color=self.colors["text_light"])
        self.users_label.pack(side="left")
        
        self.user_count = ctk.CTkLabel(self.users_header_frame, text="(0)",
                                     text_color=self.colors["text_gray"])
        self.user_count.pack(side="right", padx=10)

        # Create a frame to contain users list and scrollbar
        users_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        users_container.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        users_container.grid_columnconfigure(0, weight=1)
        users_container.grid_rowconfigure(1, weight=1)
        
        # Create a modern dropdown for user selection (for private messages)
        self.user_dropdown_var = ctk.StringVar(value="Select User")
        self.user_dropdown = ctk.CTkComboBox(
            users_container,
            values=["Select User"],
            variable=self.user_dropdown_var,
            width=180,
            command=self.on_user_selected,
            fg_color=self.colors["input_bg"],
            border_color=self.colors["separator"],
            button_color=self.colors["accent"],
            button_hover_color=self.colors["accent_hover"],
            dropdown_fg_color=self.colors["input_bg"],
            dropdown_hover_color=self.colors["accent"],
            dropdown_text_color=self.colors["text_light"]
        )
        self.user_dropdown.grid(row=0, column=0, sticky="new", pady=(0, 10))
        
        # Scrollable frame for users with modern styling
        self.users_list = ctk.CTkTextbox(users_container, 
                                        width=180, 
                                        height=300,
                                        fg_color=self.colors["sidebar_bg"],
                                        text_color=self.colors["text_light"],
                                        font=ctk.CTkFont(size=13),
                                        border_width=0)
        self.users_list.grid(row=1, column=0, sticky="nsew")
        
        # Add a modern scrollbar
        users_scrollbar = ctk.CTkScrollbar(users_container, command=self.users_list.yview)
        users_scrollbar.grid(row=1, column=1, sticky="ns")
        
        # Connect scrollbar to textbox
        self.users_list.configure(yscrollcommand=users_scrollbar.set)
        
        # Controls with modern styling
        self.users_controls = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.users_controls.grid(row=3, column=0, padx=10, pady=(5, 10), sticky="ew")
        
        self.refresh_btn = ctk.CTkButton(self.users_controls, 
                                        text="Refresh", 
                                        command=self.refresh_users,
                                        width=90,
                                        height=32,
                                        fg_color=self.colors["accent"],
                                        hover_color=self.colors["accent_hover"],
                                        corner_radius=8,
                                        font=ctk.CTkFont(size=12))
        self.refresh_btn.pack(side="left", padx=(0, 5))
        
        self.auto_refresh = ctk.CTkSwitch(self.users_controls, 
                                         text="Auto", 
                                         command=self.auto_refresh_users,
                                         switch_height=16,
                                         switch_width=36,
                                         fg_color=self.colors["separator"],
                                         progress_color=self.colors["accent"])
        self.auto_refresh.pack(side="left")
        self.auto_refresh.select()  # Enable auto-refresh by default

    def setup_chat_area(self):
        """Setup the main chat display area with modern styling"""
        self.chat_frame = ctk.CTkFrame(self, fg_color=self.colors["chat_bg"])
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        self.chat_frame.grid_rowconfigure(1, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # Chat header with modern styling
        self.chat_header = ctk.CTkFrame(self.chat_frame, 
                                       height=50, 
                                       fg_color=self.colors["chat_bg"],
                                       corner_radius=0)
        self.chat_header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.chat_header.grid_propagate(False)
        
        # Chat mode label with icon
        self.chat_mode_label = ctk.CTkLabel(self.chat_header, 
                                          text="📢 Broadcast Chat", 
                                          font=ctk.CTkFont(size=15, weight="bold"),
                                          text_color=self.colors["text_light"])
        self.chat_mode_label.pack(side="left", padx=15, pady=10)
        
        # Add a subtle separator
        separator = ctk.CTkFrame(self.chat_frame, height=1, fg_color=self.colors["separator"])
        separator.grid(row=0, column=0, sticky="ew", padx=0, pady=(50, 0))

        # Create a frame to contain chat display and scrollbar
        chat_container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        chat_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        chat_container.grid_columnconfigure(0, weight=1)
        chat_container.grid_rowconfigure(0, weight=1)
        
        # Chat display with modern styling
        self.chat_display = ctk.CTkTextbox(chat_container, 
                                         wrap="word", 
                                         font=ctk.CTkFont(size=13),
                                         fg_color=self.colors["chat_bg"],
                                         text_color=self.colors["text_light"],
                                         border_width=0)
        self.chat_display.grid(row=0, column=0, sticky="nsew")
        self.chat_display.configure(state="disabled")
        
        # Add a modern scrollbar
        chat_scrollbar = ctk.CTkScrollbar(chat_container, command=self.chat_display.yview)
        chat_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Connect scrollbar to textbox
        self.chat_display.configure(yscrollcommand=chat_scrollbar.set)

    def setup_input_area(self):
        """Setup the message input area with modern styling"""
        self.input_frame = ctk.CTkFrame(self, fg_color=self.colors["chat_bg"])
        self.input_frame.grid(row=1, column=1, sticky="ew", padx=10, pady=(0, 10))
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        # Add a subtle separator at the top
        separator = ctk.CTkFrame(self.input_frame, height=1, fg_color=self.colors["separator"])
        separator.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 10))
        
        # Message type selector with modern styling
        self.msg_type_frame = ctk.CTkFrame(self.input_frame, fg_color="transparent")
        self.msg_type_frame.grid(row=1, column=0, columnspan=2, padx=15, pady=(0, 10), sticky="w")
        
        self.msg_type = tk.StringVar(value="broadcast")
        
        self.broadcast_radio = ctk.CTkRadioButton(self.msg_type_frame, 
                                               text="Broadcast", 
                                               variable=self.msg_type, 
                                               value="broadcast",
                                               command=self.update_chat_mode,
                                               fg_color=self.colors["accent"],
                                               border_color=self.colors["text_gray"],
                                               text_color=self.colors["text_light"])
        self.broadcast_radio.pack(side="left", padx=(0, 20))
        
        self.private_radio = ctk.CTkRadioButton(self.msg_type_frame, 
                                             text="Private", 
                                             variable=self.msg_type, 
                                             value="private",
                                             command=self.update_chat_mode,
                                             fg_color=self.colors["accent"],
                                             border_color=self.colors["text_gray"],
                                             text_color=self.colors["text_light"])
        self.private_radio.pack(side="left")
        
        # Message input container for a more cohesive look
        input_container = ctk.CTkFrame(self.input_frame, fg_color=self.colors["input_bg"], corner_radius=10)
        input_container.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 15), sticky="ew")
        input_container.grid_columnconfigure(0, weight=1)
        
        # Message input with modern styling
        self.msg_input = ctk.CTkTextbox(input_container, 
                                      height=60, 
                                      wrap="word", 
                                      font=ctk.CTkFont(size=13),
                                      fg_color="transparent",
                                      border_width=0,
                                      text_color=self.colors["text_light"])
        self.msg_input.grid(row=0, column=0, padx=(15, 5), pady=10, sticky="ew")
        self.msg_input.bind("<Return>", self.handle_return)
        
        # Hint text for empty input
        self.msg_input.insert("1.0", "Type your message here...")
        self.msg_input.configure(text_color=self.colors["text_gray"])
        self.msg_input.bind("<FocusIn>", self.clear_hint_text)
        self.msg_input.bind("<FocusOut>", self.restore_hint_text)
        
        # Send button with modern styling
        self.send_btn = ctk.CTkButton(input_container, 
                                    text="Send", 
                                    width=80,
                                    height=35, 
                                    command=self.send_message,
                                    font=ctk.CTkFont(size=13, weight="bold"),
                                    fg_color=self.colors["accent"],
                                    hover_color=self.colors["accent_hover"],
                                    corner_radius=8)
        self.send_btn.grid(row=0, column=1, padx=(0, 10), pady=10)

    def update_chat_mode(self):
        """Update the chat header based on the selected mode"""
        if self.msg_type.get() == "broadcast":
            self.chat_mode_label.configure(text="📢 Broadcast Chat")
        else:
            try:
                selection = self.users_list.get("sel.first", "sel.last").strip()
                username = selection.split(" ", 1)[1]  # Remove the bullet point
                self.chat_mode_label.configure(text=f"💬 Private Chat with {username}")
            except tk.TclError:
                self.chat_mode_label.configure(text="💬 Private Chat (select a user)")

    def clear_hint_text(self, event):
        """Clear the hint text when the input gets focus"""
        if self.msg_input.get("1.0", "end-1c").strip() == "Type your message here...":
            self.msg_input.delete("1.0", "end")
            self.msg_input.configure(text_color=self.colors["text_light"])  # Normal text color

    def on_user_selected(self, selected_user):
        """Handle user selection from dropdown"""
        if selected_user and selected_user != "Select User":
            self.selected_user = selected_user
            self.chat_mode_label.configure(text=f"💬 Private Chat with {selected_user}")
            self.msg_type.set("private")
            self.add_system_message(f"Private chat with {selected_user} started. Messages will only be sent to this user.")
        else:
            self.selected_user = None
            self.chat_mode_label.configure(text="📢 Broadcast Chat")
            self.msg_type.set("broadcast")
            self.add_system_message("Switched to broadcast mode. Messages will be sent to all users.")
            
    def restore_hint_text(self, event):
        """Restore the hint text when the input loses focus (if empty)"""
        if not self.msg_input.get("1.0", "end-1c").strip():
            self.msg_input.delete("1.0", "end")
            self.msg_input.insert("1.0", "Type your message here...")
            self.msg_input.configure(text_color=self.colors["text_gray"])

    def handle_return(self, event):
        """Handle pressing Return in the message input"""
        if not event.state & 0x1:  # Check if Shift is not pressed
            self.send_message()
            return "break"  # Prevents the newline from being inserted
        return None  # Allows Shift+Enter to insert a newline

    def send_message(self):
        """Send a message based on the current chat mode"""
        message = self.msg_input.get("1.0", "end-1c").strip()
        if not message or message == "Type your message here...":
            return

        if self.msg_type.get() == "broadcast":
            # Broadcast message
            try:
                self.send_broadcast(f"[From {self.username}]: {message}")
                self.add_message("You (Broadcast)", message, "#4CAF50")  # Green for own messages
            except Exception as e:
                self.add_message("System", f"Failed to send broadcast: {e}", "#F44336")
                self.show_notification("Error", f"Failed to send broadcast: {e}", "error")
        else:
            # Private message - use selected_user from dropdown
            if not self.selected_user:
                self.add_message("System", "Please select a user from the dropdown for private messages", "#F44336")
                self.show_notification("Error", "No user selected for private message", "error")
                return
                
            try:
                self.send_private_msg(self.selected_user, message)
                self.add_message(f"You → {self.selected_user}", message, "#2196F3")  # Blue for own messages
            except Exception as e:
                self.add_message("System", f"Failed to send private message: {e}", "#F44336")
                self.show_notification("Error", f"Failed to send private message: {e}", "error")
                return

        self.msg_input.delete("1.0", "end")
        self.msg_input.insert("1.0", "Type your message here...")
        self.msg_input.configure(text_color="gray")

    def add_message(self, sender: str, message: str, color: Optional[str] = None):
        """Add a message to the chat display with modern styling"""
        # Check if chat_display exists - it might not if we've switched to a different view
        if not hasattr(self, "chat_display") or not self.chat_display.winfo_exists():
            print(f"Warning: Cannot add message - chat display not available: {sender}: {message}")
            return
            
        self.chat_display.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M")
        
        # Insert a small space before new messages for better readability
        self.chat_display.insert("end", "\n")
        
        # Create different styled messages based on sender
        if sender.startswith("You"):
            # Sent messages aligned to right
            self.chat_display.insert("end", f"{timestamp}  ", "small_text")
            self.chat_display.insert("end", f"{message}\n", "sent_message")
        elif sender == "System":
            # System messages centered with distinct styling
            self.chat_display.insert("end", f"--- {message} ---\n", "system_message")
        else:
            # Received messages aligned to left
            if "→" not in sender:  # Regular message, not a private one
                self.chat_display.insert("end", f"{sender} ({timestamp})\n", "sender_name")
                self.chat_display.insert("end", f"{message}\n", "received_message")
            else:
                # Private message sent to someone
                self.chat_display.insert("end", f"{sender} ({timestamp})\n", "private_sender")
                self.chat_display.insert("end", f"{message}\n", "sent_message")
        
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
        
    def format_chat_display(self):
        """Format the chat display with modern text styles"""
        try:
            # Create styles for different message types
            import tkinter as tk
            text_widget = self.chat_display._textbox
            
            # Define tags for different message styles
            text_widget.tag_configure("sent_message", justify="right", lmargin1=100, lmargin2=100)
            text_widget.tag_configure("received_message", lmargin1=20, lmargin2=20)
            text_widget.tag_configure("system_message", justify="center", foreground="#FF8C00")
            text_widget.tag_configure("sender_name", foreground="#8E8E8E", font=ctk.CTkFont(size=11))
            text_widget.tag_configure("private_sender", foreground="#64B5F6", font=ctk.CTkFont(size=11))
            text_widget.tag_configure("small_text", foreground="#8E8E8E", font=ctk.CTkFont(size=10))
        except (AttributeError, tk.TclError) as e:
            print(f"Warning: Could not configure text tags: {e}")
        
    def auto_refresh_users(self):
        """Auto-refresh the users list periodically"""
        self.refresh_users()
        # Schedule the next refresh
        self._auto_refresh_id = self.after(5000, self.auto_refresh_users)

    def refresh_users(self):
        """Refresh the list of online users"""
        if self.get_peers:
            try:
                peers = self.get_peers()
                
                # Clear the users list
                self.users_list.configure(state="normal")
                self.users_list.delete("1.0", "end")
        
                # Update the dropdown for user selection
                dropdown_values = ["Select User"]
                dropdown_values.extend(peers)
                self.user_dropdown.configure(values=dropdown_values)
                
                # Update the count
                self.user_count.configure(text=f"({len(peers)})")
        
                # Display each user
                if peers:
                    for username in peers:
                        self.users_list.insert("end", f"• {username}\n")
                else:
                    self.users_list.insert("end", "No users online")
        
                self.users_list.configure(state="normal")  # Keep it normal to allow selection
                
                # Show notification if auto-refresh is off
                if hasattr(self, 'auto_refresh') and not self.auto_refresh.get():
                    self.show_notification("Users Refreshed", f"Found {len(peers)} online users", "info", 2000)
                
            except Exception as e:
                self.show_notification("Error", f"Failed to refresh users: {e}", "error")
        else:
            self.show_notification("Error", "User discovery not available", "error")

    def add_system_message(self, message: str):
        """Add a system message to the chat display"""
        # Check if we're in the chat view before adding messages
        if not hasattr(self, "chat_display") or not self.chat_display.winfo_exists():
            print(f"System message (not displayed): {message}")
            return
        
        self.add_message("System", message)
        
    def show_notification(self, title, message, notification_type="info", duration=3000):
        """Show a notification popup with specified title, message, type and duration"""
        from .notification import Notification
        notification = Notification(
            title=title,
            message=message,
            notification_type=notification_type,
            duration=duration,
            master=self
        )
        notification.show()
        
    def show_settings(self):
        """Show settings in the main window"""
        # Clear the chat area to show settings
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
            
        # Configure the chat frame for settings
        self.chat_frame.grid_rowconfigure(0, weight=0)
        self.chat_frame.grid_rowconfigure(1, weight=1)
        self.chat_frame.grid_rowconfigure(2, weight=0)
        
        # Header
        header_frame = ctk.CTkFrame(self.chat_frame, fg_color=self.colors["sidebar_bg"], corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")
        
        # Settings title with back button
        title_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_container.pack(fill="x", pady=10, padx=15)
        
        back_btn = ctk.CTkButton(title_container, 
                               text="← Back", 
                               width=80,
                               command=self.setup_chat_area,
                               fg_color=self.colors["input_bg"],
                               hover_color=self.colors["accent"],
                               corner_radius=8)
        back_btn.pack(side="left")
        
        title_label = ctk.CTkLabel(title_container, text="⚙️ Settings", 
                                 font=ctk.CTkFont(size=20, weight="bold"),
                                 text_color=self.colors["text_light"])
        title_label.pack(side="left", padx=20)
        
        # Content frame with scrolling
        content_container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        content_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        content_container.grid_columnconfigure(0, weight=1)
        content_container.grid_rowconfigure(0, weight=1)
        
        # Create a scrollable frame for content
        settings_scroll = ctk.CTkScrollableFrame(content_container, fg_color="transparent")
        settings_scroll.grid(row=0, column=0, sticky="nsew")
        
        # User profile section
        profile_label = ctk.CTkLabel(settings_scroll, text="User Profile",
                                   font=ctk.CTkFont(size=16, weight="bold"),
                                   text_color=self.colors["text_light"])
        profile_label.pack(anchor="w", pady=(0, 10))
        
        # User profile frame
        profile_frame = ctk.CTkFrame(settings_scroll, fg_color=self.colors["chat_bg"])
        profile_frame.pack(fill="x", pady=(0, 15), ipady=10)
        
        # Username field
        username_frame = ctk.CTkFrame(profile_frame, fg_color="transparent")
        username_frame.pack(fill="x", padx=15, pady=5)
        
        username_label = ctk.CTkLabel(username_frame, text="Username:",
                                    width=120,
                                    anchor="w",
                                    font=ctk.CTkFont(size=13),
                                    text_color=self.colors["text_gray"])
        username_label.pack(side="left")
        
        self.username_update_entry = ctk.CTkEntry(username_frame,
                                               placeholder_text="Enter new username",
                                               font=ctk.CTkFont(size=13),
                                               fg_color=self.colors["input_bg"],
                                               text_color=self.colors["text_light"],
                                               width=200)
        self.username_update_entry.pack(side="right")
        
        # Pre-fill with current username
        self.username_update_entry.insert(0, self.username)
        
        # Update username button
        update_username_btn = ctk.CTkButton(profile_frame,
                                          text="Update Username",
                                          command=self.update_username,
                                          font=ctk.CTkFont(size=13),
                                          fg_color=self.colors["accent"],
                                          hover_color=self.colors["accent_hover"])
        update_username_btn.pack(padx=15, pady=10)
        
        # Appearance section
        appearance_label = ctk.CTkLabel(settings_scroll, text="Appearance",
                                      font=ctk.CTkFont(size=16, weight="bold"),
                                      text_color=self.colors["text_light"])
        appearance_label.pack(anchor="w", pady=(0, 10))
        
        # Appearance frame
        appearance_frame = ctk.CTkFrame(settings_scroll, fg_color=self.colors["chat_bg"])
        appearance_frame.pack(fill="x", pady=(0, 15), ipady=10)
        
        # Mode selector
        mode_frame = ctk.CTkFrame(appearance_frame, fg_color="transparent")
        mode_frame.pack(fill="x", padx=15, pady=5)
        
        mode_label = ctk.CTkLabel(mode_frame, text="Theme Mode:",
                                width=120,
                                anchor="w",
                                font=ctk.CTkFont(size=13),
                                text_color=self.colors["text_gray"])
        mode_label.pack(side="left")
        
        appearance_combobox = ctk.CTkComboBox(mode_frame, 
                                            values=self.appearance_mode_options,
                                            variable=self.appearance_mode_var, 
                                            command=self.change_appearance_mode,
                                            width=200,
                                            border_color=self.colors["accent"],
                                            button_color=self.colors["accent"],
                                            button_hover_color=self.colors["accent_hover"],
                                            dropdown_fg_color=self.colors["input_bg"])
        appearance_combobox.pack(side="right")
        
        # Color theme selector
        color_frame = ctk.CTkFrame(appearance_frame, fg_color="transparent")
        color_frame.pack(fill="x", padx=15, pady=5)
        
        color_label = ctk.CTkLabel(color_frame, text="Color Theme:",
                                 width=120,
                                 anchor="w",
                                 font=ctk.CTkFont(size=13),
                                 text_color=self.colors["text_gray"])
        color_label.pack(side="left")
        
        theme_combobox = ctk.CTkComboBox(color_frame, 
                                       values=self.color_theme_options,
                                       variable=self.color_theme_var,
                                       command=self.change_color_theme,
                                       width=200,
                                       border_color=self.colors["accent"],
                                       button_color=self.colors["accent"],
                                       button_hover_color=self.colors["accent_hover"],
                                       dropdown_fg_color=self.colors["input_bg"])
        theme_combobox.pack(side="right")
        
        # Network section
        network_label = ctk.CTkLabel(settings_scroll, text="Network",
                                   font=ctk.CTkFont(size=16, weight="bold"),
                                   text_color=self.colors["text_light"])
        network_label.pack(anchor="w", pady=(0, 10))
        
        # Network settings frame
        network_settings = ctk.CTkFrame(settings_scroll, fg_color=self.colors["chat_bg"])
        network_settings.pack(fill="x", pady=(0, 15), ipady=10)
        
        # Network refresh interval
        refresh_frame = ctk.CTkFrame(network_settings, fg_color="transparent")
        refresh_frame.pack(fill="x", padx=15, pady=5)
        
        refresh_label = ctk.CTkLabel(refresh_frame, text="Auto Refresh:",
                                   width=120,
                                   anchor="w",
                                   font=ctk.CTkFont(size=13),
                                   text_color=self.colors["text_gray"])
        refresh_label.pack(side="left")
        
        self.refresh_var = tk.StringVar(value="5")
        refresh_options = ["3", "5", "10", "30", "60"]
        
        refresh_combo = ctk.CTkComboBox(refresh_frame, 
                                      values=refresh_options,
                                      variable=self.refresh_var,
                                      command=self.change_refresh_interval,
                                      width=200,
                                      border_color=self.colors["accent"],
                                      button_color=self.colors["accent"],
                                      button_hover_color=self.colors["accent_hover"],
                                      dropdown_fg_color=self.colors["input_bg"])
        refresh_combo.pack(side="right")
        
        # DHCP Server Settings
        dhcp_frame = ctk.CTkFrame(network_settings, fg_color="transparent")
        dhcp_frame.pack(fill="x", padx=15, pady=5)
        
        dhcp_label = ctk.CTkLabel(dhcp_frame, text="DHCP Server:",
                                width=120,
                                anchor="w",
                                font=ctk.CTkFont(size=13),
                                text_color=self.colors["text_gray"])
        dhcp_label.pack(side="left")
        
        # Check if we have a reference to the app for getting DHCP status
        dhcp_enabled = False
        try:
            import gc
            from main import ZTalkApp
            app_instances = [obj for obj in gc.get_objects() if isinstance(obj, ZTalkApp)]
            if app_instances:
                app = app_instances[0]
                dhcp_status = app.get_dhcp_status()
                dhcp_enabled = dhcp_status.get("enabled", False)
        except Exception:
            pass
            
        self.dhcp_var = tk.BooleanVar(value=dhcp_enabled)
        
        dhcp_switch = ctk.CTkSwitch(dhcp_frame,
                                  text="",
                                  variable=self.dhcp_var,
                                  command=self.toggle_dhcp_server,
                                  width=50,
                                  switch_width=50,
                                  button_color=self.colors["accent"],
                                  button_hover_color=self.colors["accent_hover"],
                                  progress_color=self.colors["accent"])
        dhcp_switch.pack(side="left", padx=(5, 0))
        
        dhcp_info_button = ctk.CTkButton(dhcp_frame,
                                      text="Configure",
                                      command=self.show_dhcp_settings,
                                      width=100,
                                      height=30,
                                      fg_color=self.colors["button_bg"],
                                      hover_color=self.colors["button_hover"],
                                      font=ctk.CTkFont(size=13))
        dhcp_info_button.pack(side="right")
        
        # Add a warning label below the DHCP switch
        dhcp_warning = ctk.CTkLabel(network_settings, 
                                  text="⚠️ DHCP server should only be enabled in specific scenarios like creating ad-hoc networks.",
                                  font=ctk.CTkFont(size=12, slant="italic"),
                                  text_color="#FFD700",
                                  wraplength=400)
        dhcp_warning.pack(padx=15, pady=(0, 5), anchor="w")
        
        # About section
        about_label = ctk.CTkLabel(settings_scroll, text="About",
                                 font=ctk.CTkFont(size=16, weight="bold"),
                                 text_color=self.colors["text_light"])
        about_label.pack(anchor="w", pady=(0, 10))
        
        # About frame
        about_frame = ctk.CTkFrame(settings_scroll, fg_color=self.colors["chat_bg"])
        about_frame.pack(fill="x", pady=(0, 15), ipady=10)
        
        # App info
        app_info = ctk.CTkLabel(about_frame, 
                              text="ZTalk v1.0.0\nCross-platform P2P Chat Application",
                              font=ctk.CTkFont(size=13),
                              text_color=self.colors["text_light"])
        app_info.pack(pady=10)
        
        # Save/Apply button
        apply_button = ctk.CTkButton(self.chat_frame, 
                                   text="Apply Settings", 
                                   command=self.setup_chat_area,
                                   fg_color=self.colors["accent"],
                                   hover_color=self.colors["accent_hover"],
                                   corner_radius=8,
                                   height=40,
                                   font=ctk.CTkFont(size=14, weight="bold"))
        apply_button.grid(row=2, column=0, padx=20, pady=20, sticky="ew")
        
    def update_username(self):
        """Update the username with real-time propagation"""
        # Get the new username from the entry
        new_username = self.username_update_entry.get().strip()
        
        # Validate the username
        if not new_username:
            self.show_notification("Error", "Username cannot be empty", "error")
            return
        
        if new_username == self.username:
            self.show_notification("Info", "Username is unchanged", "info")
            return
        
        # Confirm the change
        confirm = CTkMessagebox(
            title="Confirm Username Change",
            message=f"Are you sure you want to change your username from '{self.username}' to '{new_username}'?\n\n"
                    "This will cause you to reconnect to the network.",
            icon="question",
            option_1="Cancel",
            option_2="Change"
        )
        
        response = confirm.get()
        if response != "Change":
            return
        
        # Store the old username for comparison
        old_username = self.username
        
        # Update the username in the UI
        self.username = new_username
        self.title(f"ZTalk - {new_username}")
        
        # Update profile display if it exists
        if hasattr(self, 'username_label') and self.username_label:
            self.username_label.configure(text=new_username)
        
        # If there's an avatar with initial, update it
        if hasattr(self, 'avatar_initial') and self.avatar_initial:
            self.avatar_initial.configure(text=new_username[0].upper())
        
        # Display a notification
        self.show_notification("Success", f"Username changed to {new_username}", "success")
        
        # Update system message
        self.add_system_message(f"Username changed from {old_username} to {new_username}")
        
        # If there's a callback or a method to propagate the change to the network, call it
        try:
            # Call any registered callbacks for username change
            if hasattr(self, 'on_username_change') and callable(self.on_username_change):
                self.on_username_change(new_username)
                
            # Trigger re-registration in service discovery if available
            if hasattr(self, 'service_discovery') and hasattr(self.service_discovery, 'update_service'):
                self.service_discovery.update_service(new_username)
                
            # If the main app is accessible and has a method to handle username changes
            # This assumes the app stores a reference to ChatWindow and can access it
            from main import ZTalkApp
            app_instances = [obj for obj in gc.get_objects() if isinstance(obj, ZTalkApp)]
            if app_instances:
                app = app_instances[0]
                if hasattr(app, 'update_username') and callable(app.update_username):
                    app.update_username(new_username)
                    
        except Exception as e:
            self.show_notification("Warning", f"Username changed locally but may not be propagated: {e}", "warning")
            self.add_system_message(f"Failed to propagate username change: {e}")
        
        # Return to chat view after applying the change
        self.setup_chat_area()

    def change_appearance_mode(self, new_mode):
        """Change the appearance mode"""
        mode_map = {
            "Light": "light",
            "Dark": "dark",
            "System": "system"
        }
        ctk.set_appearance_mode(mode_map[new_mode])
    
    def change_color_theme(self, new_theme):
        """Change the color theme"""
        theme_map = {
            "Blue": "blue",
            "Dark Blue": "dark-blue",
            "Green": "green",
            "Purple": "dark-blue",  # CustomTkinter doesn't have a built-in purple theme
            "Teal": "green"  # CustomTkinter doesn't have a built-in teal theme
        }
        ctk.set_default_color_theme(theme_map[new_theme])
        
        # Add a system message
        self.add_system_message("Theme changed. Some changes will apply after restart")
        
    def change_refresh_interval(self, interval):
        """Change the auto-refresh interval for network and users"""
        try:
            seconds = int(interval)
            # Update the refresh timers
            if hasattr(self, "_auto_refresh_id") and self._auto_refresh_id:
                self.after_cancel(self._auto_refresh_id)
            self._auto_refresh_id = self.after(seconds * 1000, self.auto_refresh_users)
            self.add_system_message(f"Auto-refresh interval set to {seconds} seconds")
        except (ValueError, Exception) as e:
            print(f"Error changing refresh interval: {e}")
            self.add_system_message("Could not change refresh interval")

    def on_closing(self):
        """Handle window closing"""
        print("Closing ZTalk application...")
        
        # Close any active SSH connections
        if hasattr(self, 'terminal') and hasattr(self.terminal, 'command_handler'):
            # There's an active SSH session, try to close it
            from utils.ssh_utils import close_ssh_connection
            try:
                # Send exit command to the terminal if possible
                self.terminal.append_text("Closing SSH connection...\n", "info")
                if hasattr(self, '_ssh_connection') and self._ssh_connection:
                    close_ssh_connection(self._ssh_connection)
            except Exception as e:
                print(f"Error closing SSH connection: {e}")
                
        # Cancel any scheduled auto-refresh tasks
        if self._auto_refresh_id:
            try:
                self.after_cancel(self._auto_refresh_id)
            except Exception as e:
                print(f"Error canceling auto-refresh: {e}")
            
        # Close SSH client if open
        if hasattr(self, 'ssh_client') and self.ssh_client and self.ssh_client.winfo_exists():
            try:
                self.ssh_client.on_close()
            except Exception as e:
                print(f"Error closing SSH client window: {e}")
            
        # Force all threads to be daemon so they don't prevent exit
        for thread in threading.enumerate():
            if thread != threading.current_thread() and not thread.daemon:
                try:
                    print(f"Setting thread {thread.name} to daemon")
                    thread.daemon = True
                except:
                    pass
                    
        # This will trigger shutdown process in main app
        print("Quitting application...")
        self.quit()
        self.destroy()
        
        # Force exit if needed
        import os
        import sys
        os._exit(0)

    def setup_utility_buttons(self):
        """Setup utility buttons with modern styling"""
        # Utility section header
        utility_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        utility_header.grid(row=4, column=0, padx=10, pady=(20, 5), sticky="ew")
        
        utility_label = ctk.CTkLabel(utility_header, text="Tools & Utilities",
                                  font=ctk.CTkFont(size=14, weight="bold"),
                                  text_color=self.colors["text_light"])
        utility_label.pack(side="left")
        
        # Utility buttons in a modern container
        self.utility_frame = ctk.CTkFrame(self.sidebar, fg_color=self.colors["sidebar_bg"])
        self.utility_frame.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        # SSH button with emoji icon
        self.ssh_btn = ctk.CTkButton(
            self.utility_frame, 
            text="🖥️  SSH Client",
            command=self.open_ssh_client,
            fg_color=self.colors["input_bg"],
            hover_color=self.colors["accent"],
            corner_radius=8,
            height=40,
            anchor="w",
            font=ctk.CTkFont(size=13)
        )
        self.ssh_btn.pack(pady=5, fill="x", padx=5)
        
        # Network info button with emoji icon
        self.network_btn = ctk.CTkButton(
            self.utility_frame, 
            text="🌐  Network Info",
            command=self.show_network_info,
            fg_color=self.colors["input_bg"],
            hover_color=self.colors["accent"],
            corner_radius=8,
            height=40,
            anchor="w",
            font=ctk.CTkFont(size=13)
        )
        self.network_btn.pack(pady=5, fill="x", padx=5)
        
        # Settings button with emoji icon
        self.settings_btn_main = ctk.CTkButton(
            self.utility_frame, 
            text="⚙️  Settings",
            command=self.show_settings,
            fg_color=self.colors["input_bg"],
            hover_color=self.colors["accent"],
            corner_radius=8,
            height=40,
            anchor="w",
            font=ctk.CTkFont(size=13)
        )
        self.settings_btn_main.pack(pady=5, fill="x", padx=5)
        
    def open_ssh_client(self):
        """Open the SSH client in the main display area"""
        # Clear the chat area to show SSH client
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
            
        # Configure the chat frame for terminal
        self.chat_frame.grid_rowconfigure(0, weight=0)  # Header
        self.chat_frame.grid_rowconfigure(1, weight=1)  # Terminal content
        self.chat_frame.grid_columnconfigure(0, weight=1)
        
        # Header with back button
        header_frame = ctk.CTkFrame(self.chat_frame, fg_color=self.colors["sidebar_bg"], corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")
        
        # Title with back button
        title_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_container.pack(fill="x", pady=10, padx=15)
        
        back_btn = ctk.CTkButton(title_container, 
                               text="← Back", 
                               width=80,
                               command=self.setup_chat_area,
                               fg_color=self.colors["input_bg"],
                               hover_color=self.colors["accent"],
                               corner_radius=8)
        back_btn.pack(side="left")
        
        title_label = ctk.CTkLabel(title_container, text="SSH Client", 
                                 font=ctk.CTkFont(size=20, weight="bold"),
                                 text_color=self.colors["text_light"])
        title_label.pack(side="left", padx=20)
        
        # Content area
        self.terminal_container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        self.terminal_container.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        
        # Create terminal widget
        try:
            # Import here to avoid circular imports
            from .terminal_widget import TerminalWidget
            
            # Create the terminal widget (remove fg_color which isn't supported)
            self.terminal = TerminalWidget(
                name="SSH Terminal",
                on_input=self.on_terminal_input,
                on_exit=self.on_terminal_exit
            )
            
            # Add some welcome text
            self.terminal.add_output("SSH Terminal initialized.\n")
            self.terminal.add_output("Use the connect button below to establish a connection.\n\n")
            
            # Show terminal
            self.terminal.run()
        except Exception as e:
            self.show_notification("Error", f"Failed to initialize terminal: {e}", "error")
            print(f"Terminal error: {e}")
            self.setup_chat_area()  # Go back to chat
        
    def toggle_network_detection(self):
        """Toggle between automatic and manual network settings"""
        value = self.use_network_detection.get()
        if not value:
            # Create manual network config frame if not using auto detection
            if not hasattr(self, "manual_net_frame"):
                self.manual_net_frame = ctk.CTkFrame(self.terminal_container, fg_color=self.colors["input_bg"])
                self.manual_net_frame.pack(fill="x", pady=(0, 10))
                
                info_label = ctk.CTkLabel(self.manual_net_frame, 
                                       text="Specify which network interface to use:", 
                                       font=ctk.CTkFont(size=13))
                info_label.pack(padx=15, pady=(10, 5), anchor="w")
                
                iface_frame = ctk.CTkFrame(self.manual_net_frame, fg_color="transparent")
                iface_frame.pack(fill="x", padx=15, pady=5)
                
                # List available interfaces
                active_interfaces = list(self.network_manager.active_interfaces.items())
                labels = [f"{name} ({ip})" for name, ip in active_interfaces]
                values = [ip for _, ip in active_interfaces]
                
                if not values:
                    labels = ["No interfaces found"]
                    values = ["127.0.0.1"]
                    
                self.iface_label = ctk.CTkLabel(iface_frame, text="Interface:", width=80)
                self.iface_label.pack(side="left")
                
                self.iface_dropdown = ctk.CTkComboBox(
                    iface_frame,
                    values=labels,
                    variable=tk.StringVar(value=labels[0] if labels else ""),
                    width=250
                )
                self.iface_dropdown.pack(side="left", padx=5)
                
                # Manual IP entry
                manual_frame = ctk.CTkFrame(self.manual_net_frame, fg_color="transparent")
                manual_frame.pack(fill="x", padx=15, pady=5)
                
                self.use_manual_ip = ctk.CTkSwitch(
                    manual_frame, 
                    text="Use custom source IP address",
                    variable=tk.BooleanVar(value=False),
                    switch_width=40,
                    switch_height=20,
                    corner_radius=10,
                    command=self.toggle_manual_ip
                )
                self.use_manual_ip.pack(side="left")
                
                self.manual_ip_frame = ctk.CTkFrame(self.manual_net_frame, fg_color="transparent")
                self.manual_ip_frame.pack(fill="x", padx=15, pady=5)
                
                ip_label = ctk.CTkLabel(self.manual_ip_frame, text="Source IP:", width=80)
                ip_label.pack(side="left")
                
                self.manual_ip = ctk.CTkEntry(self.manual_ip_frame, placeholder_text="192.168.1.2")
                self.manual_ip.pack(side="left", fill="x", expand=True, padx=5)
                
                # Hide initially
                self.manual_ip_frame.pack_forget()
            else:
                self.manual_net_frame.pack(fill="x", pady=(0, 10))
        else:
            # Hide manual network config
            if hasattr(self, "manual_net_frame"):
                self.manual_net_frame.pack_forget()
        
    def toggle_manual_ip(self):
        """Toggle manual IP entry field"""
        if self.use_manual_ip.get():
            self.manual_ip_frame.pack(fill="x", padx=15, pady=5)
        else:
            self.manual_ip_frame.pack_forget()
            
    def simple_ssh_connect(self):
        """Simple SSH connection handler (placeholder)"""
        # Get connection details
        host = getattr(self, 'ssh_host', None)
        username = getattr(self, 'ssh_username', None)
        
        # Check if we have the necessary attributes
        if not hasattr(self, 'terminal'):
            self.show_notification("Error", "Terminal not initialized", "error")
            return
            
        if not host or not username or not hasattr(host, 'get') or not hasattr(username, 'get'):
            self.show_notification("Error", "Host and username are required", "error")
            if hasattr(self.terminal, 'add_output'):
                self.terminal.add_output("Error: Host and username are required\n")
            return
        
        # This would normally initiate an SSH connection
        self.show_notification("Info", "SSH connection feature not implemented yet", "info")
        if hasattr(self.terminal, 'add_output'):
            self.terminal.add_output("SSH connection feature not implemented yet.\n")
            self.terminal.add_output("This is a placeholder method.\n")

    def setup_network_status(self):
        """Setup network status indicators with modern styling"""
        if not self.network_manager:
            return
            
        # Network status header
        network_header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        network_header.grid(row=6, column=0, padx=10, pady=(20, 5), sticky="ew")
        
        network_header_label = ctk.CTkLabel(network_header, text="Network Status",
                                        font=ctk.CTkFont(size=14, weight="bold"),
                                        text_color=self.colors["text_light"])
        network_header_label.pack(side="left")
        
        # Create network info section with modern styling
        self.network_frame = ctk.CTkFrame(self.sidebar, fg_color=self.colors["sidebar_bg"])
        self.network_frame.grid(row=7, column=0, padx=10, pady=(0, 10), sticky="ew")
        
        # Status indicator with colored circle
        status_container = ctk.CTkFrame(self.network_frame, fg_color="transparent")
        status_container.pack(fill="x", pady=5, padx=10)
        
        self.network_status_indicator = ctk.CTkLabel(status_container, text="●", 
                                                  text_color="#F44336",  # Start as red
                                                  font=ctk.CTkFont(size=14))
        self.network_status_indicator.pack(side="left", padx=(0, 10))
        
        self.network_title = ctk.CTkLabel(status_container, text="Disconnected", 
                                       font=ctk.CTkFont(size=13, weight="bold"),
                                       text_color=self.colors["text_light"])
        self.network_title.pack(side="left")
        
        # Network info with icons
        # Segments info
        segments_frame = ctk.CTkFrame(self.network_frame, fg_color="transparent")
        segments_frame.pack(fill="x", pady=5, padx=10)
        
        segments_icon = ctk.CTkLabel(segments_frame, text="🔀", font=ctk.CTkFont(size=13))
        segments_icon.pack(side="left", padx=(0, 10))
        
        segments_label = ctk.CTkLabel(segments_frame, text="Network Segments:",
                                    font=ctk.CTkFont(size=12),
                                    text_color=self.colors["text_gray"])
        segments_label.pack(side="left")
        
        self.network_segments_label = ctk.CTkLabel(segments_frame, text="0",
                                               font=ctk.CTkFont(size=12, weight="bold"),
                                               text_color=self.colors["text_light"])
        self.network_segments_label.pack(side="right")
        
        # Interfaces info
        interfaces_frame = ctk.CTkFrame(self.network_frame, fg_color="transparent")
        interfaces_frame.pack(fill="x", pady=5, padx=10)
        
        interfaces_icon = ctk.CTkLabel(interfaces_frame, text="🖧", font=ctk.CTkFont(size=13))
        interfaces_icon.pack(side="left", padx=(0, 10))
        
        interfaces_label = ctk.CTkLabel(interfaces_frame, text="Active Interfaces:",
                                      font=ctk.CTkFont(size=12),
                                      text_color=self.colors["text_gray"])
        interfaces_label.pack(side="left")
        
        self.network_interfaces_label = ctk.CTkLabel(interfaces_frame, text="0",
                                                 font=ctk.CTkFont(size=12, weight="bold"),
                                                 text_color=self.colors["text_light"])
        self.network_interfaces_label.pack(side="right")
        
        # Add a view details button
        details_button = ctk.CTkButton(
            self.network_frame,
            text="View Details",
            command=self.show_network_info,
            fg_color=self.colors["input_bg"],
            hover_color=self.colors["accent"],
            corner_radius=8,
            height=30,
            font=ctk.CTkFont(size=12)
        )
        details_button.pack(pady=10, padx=10, fill="x")
        
        # Start periodic update of network status
        self.after(2000, self.update_network_status)
        
    def update_network_status(self):
        """Update network status display with visual indicators"""
        if not self.network_manager:
            return
            
        try:
            # Get network segments
            segments = self.network_manager.get_network_segments()
            self.network_segments_label.configure(text=str(len(segments)))
            
            # Get active interfaces
            interfaces = self.network_manager.get_all_active_ips()
            self.network_interfaces_label.configure(text=str(len(interfaces)))
            
            # Update UI color based on status
            if len(interfaces) > 0:
                self.network_status_indicator.configure(text_color="#4CAF50")  # Green
                self.network_title.configure(text="Connected")
            else:
                self.network_status_indicator.configure(text_color="#F44336")  # Red
                self.network_title.configure(text="Disconnected")
                
        except Exception as e:
            print(f"Error updating network status: {e}")
            
        # Schedule next update
        self.after(5000, self.update_network_status)
        
    def show_network_info(self):
        """Show detailed network information in the main window"""
        if not self.network_manager:
            self.add_system_message("Network manager not available")
            return
        
        # Clear the chat area to show network info
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
            
        # Configure the chat frame for network info
        self.chat_frame.grid_rowconfigure(0, weight=0)
        self.chat_frame.grid_rowconfigure(1, weight=1)
        self.chat_frame.grid_rowconfigure(2, weight=0)
        
        # Header
        header_frame = ctk.CTkFrame(self.chat_frame, fg_color=self.colors["sidebar_bg"], corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew")
        
        # Title with back button
        title_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_container.pack(fill="x", pady=10, padx=15)
        
        back_btn = ctk.CTkButton(title_container, 
                               text="← Back", 
                               width=80,
                               command=self.setup_chat_area,
                               fg_color=self.colors["input_bg"],
                               hover_color=self.colors["accent"],
                               corner_radius=8)
        back_btn.pack(side="left")
        
        title_label = ctk.CTkLabel(title_container, text="🌐 Network Information", 
                                 font=ctk.CTkFont(size=20, weight="bold"),
                                 text_color=self.colors["text_light"])
        title_label.pack(side="left", padx=20)
        
        # Content area
        content_container = ctk.CTkFrame(self.chat_frame, fg_color="transparent")
        content_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content_container.grid_columnconfigure(0, weight=1)
        content_container.grid_rowconfigure(0, weight=1)
        
        # Set up notebook tabs
        tab_view = ctk.CTkTabview(content_container, 
                                 fg_color=self.colors["chat_bg"],
                                 segmented_button_fg_color=self.colors["input_bg"],
                                 segmented_button_selected_color=self.colors["accent"],
                                 segmented_button_selected_hover_color=self.colors["accent_hover"],
                                 segmented_button_unselected_color=self.colors["input_bg"])
        tab_view.pack(fill="both", expand=True)
        
        # Add tabs
        tab_view.add("Interfaces")
        tab_view.add("Configuration")  # New tab for IP configuration
        tab_view.add("Segments")
        tab_view.add("Routing")
        tab_view.add("ARP Table")
        
        # Interfaces tab
        interfaces_tab = tab_view.tab("Interfaces")
        
        # Create a text widget for displaying interfaces
        interfaces_text = ctk.CTkTextbox(interfaces_tab, 
                                       wrap="none",
                                       fg_color=self.colors["chat_bg"],
                                       text_color=self.colors["text_light"],
                                       font=ctk.CTkFont(size=13, family="Consolas"))
        interfaces_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add interface information with better formatting
        interfaces_text.insert("end", "Active Network Interfaces\n", "header")
        interfaces_text.insert("end", "═════════════════════════\n\n")
        
        for interface, ip in self.network_manager.active_interfaces.items():
            interfaces_text.insert("end", f"Interface: ", "label")
            interfaces_text.insert("end", f"{interface}\n")
            interfaces_text.insert("end", f"IP Address: ", "label")
            interfaces_text.insert("end", f"{ip}\n\n")
        
        # IP Configuration tab
        config_tab = tab_view.tab("Configuration")
        
        # Create a scrollable frame for the IP configuration
        config_scroll = ctk.CTkScrollableFrame(config_tab, fg_color="transparent")
        config_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title and description
        config_title = ctk.CTkLabel(config_scroll, 
                                   text="Network Interface Configuration",
                                   font=ctk.CTkFont(size=16, weight="bold"),
                                   text_color=self.colors["text_light"])
        config_title.pack(anchor="w", pady=(0, 5))
        
        config_desc = ctk.CTkLabel(config_scroll,
                                  text="Select an interface and configure its IP settings",
                                  font=ctk.CTkFont(size=12),
                                  text_color=self.colors["text_gray"])
        config_desc.pack(anchor="w", pady=(0, 15))
        
        # Interface selector
        interface_frame = ctk.CTkFrame(config_scroll, fg_color=self.colors["chat_bg"])
        interface_frame.pack(fill="x", pady=(0, 15))
        
        interface_label = ctk.CTkLabel(interface_frame,
                                      text="Select Interface:",
                                      font=ctk.CTkFont(size=13, weight="bold"),
                                      text_color=self.colors["text_light"])
        interface_label.pack(anchor="w", padx=15, pady=(10, 5))
        
        # Get interface names and create a dropdown
        interface_names = list(self.network_manager.active_interfaces.keys())
        
        # Create StringVar for interface selection
        self.selected_interface = ctk.StringVar(value=interface_names[0] if interface_names else "No interfaces")
        
        # Interface dropdown
        interface_dropdown = ctk.CTkComboBox(interface_frame,
                                           values=interface_names,
                                           variable=self.selected_interface,
                                           command=self.on_interface_selected,
                                           width=300,
                                           height=35,
                                           fg_color=self.colors["input_bg"],
                                           border_color=self.colors["separator"],
                                           button_color=self.colors["accent"],
                                           dropdown_fg_color=self.colors["input_bg"])
        interface_dropdown.pack(padx=15, pady=(0, 10))
        
        # IP configuration frame
        self.ip_config_frame = ctk.CTkFrame(config_scroll, fg_color=self.colors["chat_bg"])
        self.ip_config_frame.pack(fill="x", pady=(0, 15))
        
        # Current IP info section
        current_ip_label = ctk.CTkLabel(self.ip_config_frame,
                                      text="Current Settings:",
                                      font=ctk.CTkFont(size=13, weight="bold"),
                                      text_color=self.colors["text_light"])
        current_ip_label.pack(anchor="w", padx=15, pady=(10, 5))
        
        # Display current IP, subnet, gateway
        self.current_ip_info = ctk.CTkTextbox(self.ip_config_frame,
                                            height=80,
                                            wrap="none",
                                            fg_color=self.colors["input_bg"],
                                            text_color=self.colors["text_light"],
                                            font=ctk.CTkFont(size=12, family="Consolas"))
        self.current_ip_info.pack(fill="x", padx=15, pady=(0, 10))
        
        # New IP configuration section
        new_ip_label = ctk.CTkLabel(self.ip_config_frame,
                                  text="New Configuration:",
                                  font=ctk.CTkFont(size=13, weight="bold"),
                                  text_color=self.colors["text_light"])
        new_ip_label.pack(anchor="w", padx=15, pady=(10, 5))
        
        # IP address input
        ip_input_frame = ctk.CTkFrame(self.ip_config_frame, fg_color="transparent")
        ip_input_frame.pack(fill="x", padx=15, pady=(5, 0))
        
        ip_label = ctk.CTkLabel(ip_input_frame,
                              text="IP Address:",
                              width=100,
                              anchor="e",
                              font=ctk.CTkFont(size=12),
                              text_color=self.colors["text_gray"])
        ip_label.pack(side="left")
        
        self.ip_entry = ctk.CTkEntry(ip_input_frame,
                                   placeholder_text="e.g., 192.168.1.100",
                                   font=ctk.CTkFont(size=12),
                                   fg_color=self.colors["input_bg"],
                                   text_color=self.colors["text_light"],
                                   height=30)
        self.ip_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        # Subnet mask input
        subnet_input_frame = ctk.CTkFrame(self.ip_config_frame, fg_color="transparent")
        subnet_input_frame.pack(fill="x", padx=15, pady=(5, 0))
        
        subnet_label = ctk.CTkLabel(subnet_input_frame,
                                  text="Subnet Mask:",
                                  width=100,
                                  anchor="e",
                                  font=ctk.CTkFont(size=12),
                                  text_color=self.colors["text_gray"])
        subnet_label.pack(side="left")
        
        self.subnet_entry = ctk.CTkEntry(subnet_input_frame,
                                       placeholder_text="e.g., 255.255.255.0",
                                       font=ctk.CTkFont(size=12),
                                       fg_color=self.colors["input_bg"],
                                       text_color=self.colors["text_light"],
                                       height=30)
        self.subnet_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        # Gateway input
        gateway_input_frame = ctk.CTkFrame(self.ip_config_frame, fg_color="transparent")
        gateway_input_frame.pack(fill="x", padx=15, pady=(5, 0))
        
        gateway_label = ctk.CTkLabel(gateway_input_frame,
                                   text="Gateway:",
                                   width=100,
                                   anchor="e",
                                   font=ctk.CTkFont(size=12),
                                   text_color=self.colors["text_gray"])
        gateway_label.pack(side="left")
        
        self.gateway_entry = ctk.CTkEntry(gateway_input_frame,
                                        placeholder_text="e.g., 192.168.1.1",
                                        font=ctk.CTkFont(size=12),
                                        fg_color=self.colors["input_bg"],
                                        text_color=self.colors["text_light"],
                                        height=30)
        self.gateway_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        # Buttons for applying changes
        buttons_frame = ctk.CTkFrame(self.ip_config_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        # Validate button
        validate_btn = ctk.CTkButton(buttons_frame,
                                   text="Validate",
                                   command=self.validate_ip_config,
                                   font=ctk.CTkFont(size=12),
                                   fg_color=self.colors["input_bg"],
                                   hover_color=self.colors["accent"],
                                   height=35,
                                   width=100)
        validate_btn.pack(side="left", padx=(0, 10))
        
        # Apply button
        apply_btn = ctk.CTkButton(buttons_frame,
                                text="Apply Changes",
                                command=self.apply_ip_config,
                                font=ctk.CTkFont(size=12, weight="bold"),
                                fg_color=self.colors["accent"],
                                hover_color=self.colors["accent_hover"],
                                height=35)
        apply_btn.pack(side="left", fill="x", expand=True)
        
        # Initialize with the first interface if available
        if interface_names:
            self.on_interface_selected(interface_names[0])
            
        # Segments tab
        segments_tab = tab_view.tab("Segments")
        
        # Create a text widget for displaying segments
        segments_text = ctk.CTkTextbox(segments_tab, 
                                     wrap="none",
                                     fg_color=self.colors["chat_bg"],
                                     text_color=self.colors["text_light"],
                                     font=ctk.CTkFont(size=13, family="Consolas"))
        segments_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add segment information with better formatting
        segments_text.insert("end", "Network Segments\n", "header")
        segments_text.insert("end", "══════════════\n\n")
        
        for network, ips in self.network_manager.network_segments.items():
            segments_text.insert("end", f"Network: ", "label")
            segments_text.insert("end", f"{network}\n")
            segments_text.insert("end", f"Connected IPs: ", "label")
            segments_text.insert("end", f"{', '.join(ips)}\n\n")
            
        # Routing tab
        routing_tab = tab_view.tab("Routing")
        
        # Create a text widget for displaying routing
        routing_text = ctk.CTkTextbox(routing_tab, 
                                    wrap="none",
                                    fg_color=self.colors["chat_bg"],
                                    text_color=self.colors["text_light"],
                                    font=ctk.CTkFont(size=13, family="Consolas"))
        routing_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add routing information with better formatting
        routing_text.insert("end", "Routing Information\n", "header")
        routing_text.insert("end", "══════════════════\n\n")
        
        primary_ip = self.network_manager.get_primary_ip() or "No primary IP detected"
        routing_text.insert("end", f"Primary IP: ", "label")
        routing_text.insert("end", f"{primary_ip}\n\n")
        
        if hasattr(self.network_manager, 'bridges') and self.network_manager.bridges:
            routing_text.insert("end", "Active Bridges:\n", "section")
            for bridge in self.network_manager.bridges:
                routing_text.insert("end", f"• {bridge}\n")
        else:
            routing_text.insert("end", "No active bridges\n")
                
        # ARP tab
        arp_tab = tab_view.tab("ARP Table")
        
        # Create a text widget for displaying ARP table
        arp_text = ctk.CTkTextbox(arp_tab, 
                                wrap="none",
                                fg_color=self.colors["chat_bg"],
                                text_color=self.colors["text_light"],
                                font=ctk.CTkFont(size=13, family="Consolas"))
        arp_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add ARP information with better formatting
        arp_text.insert("end", "ARP Table\n", "header")
        arp_text.insert("end", "═════════\n\n")
        
        if hasattr(self.network_manager, 'arp_table') and self.network_manager.arp_table:
            for network, entries in self.network_manager.arp_table.items():
                arp_text.insert("end", f"Network: {network}\n", "section")
                for ip, mac in entries.items():
                    arp_text.insert("end", f"  {ip} → ", "ip")
                    arp_text.insert("end", f"{mac}\n", "mac")
                arp_text.insert("end", "\n")
        else:
            arp_text.insert("end", "No ARP table entries available\n")
        
        # Try to format the text in the tabs
        try:
            for text_widget in [interfaces_text, segments_text, routing_text, arp_text]:
                underlying_widget = text_widget._textbox
                underlying_widget.tag_configure("header", font=("Consolas", 16, "bold"), foreground="#64B5F6")
                underlying_widget.tag_configure("section", font=("Consolas", 13, "bold"), foreground="#AED581")
                underlying_widget.tag_configure("label", font=("Consolas", 13, "bold"), foreground="#B0BEC5")
                underlying_widget.tag_configure("ip", foreground="#E1BEE7")
                underlying_widget.tag_configure("mac", foreground="#FFCC80")
        except (AttributeError, tk.TclError) as e:
            print(f"Warning: Could not format network info text: {e}")
        
        # Make all text widgets read-only
        interfaces_text.configure(state="disabled")
        segments_text.configure(state="disabled")
        routing_text.configure(state="disabled")
        arp_text.configure(state="disabled")
        
        # Close button
        close_btn = ctk.CTkButton(self.chat_frame, 
                                text="Return to Chat", 
                                command=self.setup_chat_area,
                                fg_color=self.colors["accent"],
                                hover_color=self.colors["accent_hover"],
                                corner_radius=8,
                                height=40,
                                font=ctk.CTkFont(size=14, weight="bold"))
        close_btn.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

    def on_interface_selected(self, selected_interface):
        """Handle interface selection from dropdown"""
        if selected_interface == "No interfaces":
            self.show_notification("Warning", "No network interfaces available", "warning")
            return
        
        self.update_ip_config(selected_interface)
    
    def update_ip_config(self, interface_name):
        """Update IP configuration display for the selected interface"""
        try:
            # Get current IP for the interface
            ip = self.network_manager.active_interfaces.get(interface_name, "Not available")
            
            # Clear and update the current IP info
            self.current_ip_info.configure(state="normal")
            self.current_ip_info.delete("1.0", "end")
            
            # Add interface information with better formatting
            self.current_ip_info.insert("end", f"Interface: {interface_name}\n")
            self.current_ip_info.insert("end", f"IP Address: {ip}\n")
            
            # Try to get subnet and gateway if available
            try:
                import netifaces
                addrs = netifaces.ifaddresses(interface_name)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        if 'addr' in addr and addr['addr'] == ip:
                            if 'netmask' in addr:
                                self.current_ip_info.insert("end", f"Subnet Mask: {addr['netmask']}\n")
                                # Pre-fill the subnet entry
                                self.subnet_entry.delete(0, "end")
                                self.subnet_entry.insert(0, addr['netmask'])
                            
                            # Pre-fill the IP entry
                            self.ip_entry.delete(0, "end")
                            self.ip_entry.insert(0, ip)
                            
                            # Try to get gateway
                            gateways = netifaces.gateways()
                            if 'default' in gateways and netifaces.AF_INET in gateways['default']:
                                gw_addr, gw_iface = gateways['default'][netifaces.AF_INET]
                                if gw_iface == interface_name:
                                    self.current_ip_info.insert("end", f"Gateway: {gw_addr}\n")
                                    # Pre-fill the gateway entry
                                    self.gateway_entry.delete(0, "end")
                                    self.gateway_entry.insert(0, gw_addr)
            except (ImportError, Exception) as e:
                self.current_ip_info.insert("end", f"Additional info not available: {e}\n")
                
            self.current_ip_info.configure(state="disabled")
            
        except Exception as e:
            self.show_notification("Error", f"Failed to get interface info: {e}", "error")
    
    def validate_ip_config(self):
        """Validate the IP configuration entered by the user"""
        try:
            import ipaddress
            
            # Get values from entries
            ip = self.ip_entry.get().strip()
            subnet = self.subnet_entry.get().strip()
            gateway = self.gateway_entry.get().strip()
            
            # Validate IP address
            try:
                ip_obj = ipaddress.IPv4Address(ip)
                ip_valid = True
            except ValueError:
                ip_valid = False
                self.show_notification("Error", "Invalid IP address format", "error")
                return False
            
            # Validate subnet mask
            try:
                subnet_obj = ipaddress.IPv4Address(subnet)
                # Check if it's a valid subnet mask (contiguous 1s followed by contiguous 0s)
                subnet_int = int(subnet_obj)
                subnet_bin = bin(subnet_int)[2:].zfill(32)
                if '01' in subnet_bin:  # If there's a 0 followed by a 1, it's not valid
                    subnet_valid = False
                    self.show_notification("Error", "Invalid subnet mask - not contiguous", "error")
                    return False
                subnet_valid = True
            except ValueError:
                subnet_valid = False
                self.show_notification("Error", "Invalid subnet mask format", "error")
                return False
            
            # Validate gateway (if provided)
            if gateway:
                try:
                    gateway_obj = ipaddress.IPv4Address(gateway)
                    gateway_valid = True
                except ValueError:
                    gateway_valid = False
                    self.show_notification("Error", "Invalid gateway format", "error")
                    return False
                
                # Check if gateway is in the same subnet
                try:
                    network = ipaddress.IPv4Network(f"{ip}/{subnet}", strict=False)
                    if gateway_obj not in network:
                        self.show_notification("Warning", "Gateway is not in the same subnet", "warning")
                        # Don't return here, just warn the user
                
                except ValueError as e:
                    self.show_notification("Error", f"Network validation error: {e}", "error")
                    return False
            
            # Check for IP conflicts
            if hasattr(self.network_manager, 'detect_ip_conflict'):
                conflict = self.network_manager.detect_ip_conflict(ip)
                if conflict:
                    self.show_notification("Warning", f"Potential IP conflict detected with {conflict}", "warning")
                    # Don't return here, just warn the user
            
            # If we got here, validation passed
            self.show_notification("Success", "IP configuration validated successfully", "success")
            return True
            
        except Exception as e:
            self.show_notification("Error", f"Validation error: {e}", "error")
            return False
    
    def apply_ip_config(self):
        """Apply the IP configuration to the selected interface"""
        # First validate the input
        if not self.validate_ip_config():
            return
            
        # Get values from entries
        ip = self.ip_entry.get().strip()
        subnet = self.subnet_entry.get().strip()
        gateway = self.gateway_entry.get().strip()
        interface = self.selected_interface
        
        # Show confirmation dialog
        confirm = CTkMessagebox(
            title="Confirm IP Change",
            message=f"Are you sure you want to change the IP configuration of {interface}?\n\n"
                    f"IP: {ip}\nSubnet: {subnet}\nGateway: {gateway}\n\n"
                    "This will affect network connectivity!",
            icon="question",
            option_1="Cancel",
            option_2="Apply"
        )
        
        response = confirm.get()
        if response != "Apply":
            return
        
        # Execute the IP change based on platform
        try:
            platform_system = platform.system()
            success = False
            
            if platform_system == "Windows":
                # Windows command to change IP
                import subprocess
                
                # Format the command
                netsh_cmd = (
                    f'netsh interface ip set address name="{interface}" static '
                    f'{ip} {subnet} {gateway}'
                )
                
                # Execute the command
                result = subprocess.run(netsh_cmd, shell=True, capture_output=True, text=True)
                success = result.returncode == 0
                
                if not success:
                    self.show_notification("Error", f"Failed to apply IP: {result.stderr}", "error")
                
            elif platform_system == "Linux":
                # Linux command to change IP
                import subprocess
                
                # May require sudo/root privileges
                ip_cmd = f"ip addr flush dev {interface}"
                ip_set_cmd = f"ip addr add {ip}/{self.get_cidr(subnet)} dev {interface}"
                ip_up_cmd = f"ip link set {interface} up"
                gw_cmd = f"ip route add default via {gateway} dev {interface}"
                
                # Execute commands
                try:
                    subprocess.run(ip_cmd, shell=True, check=True)
                    subprocess.run(ip_set_cmd, shell=True, check=True)
                    subprocess.run(ip_up_cmd, shell=True, check=True)
                    subprocess.run(gw_cmd, shell=True, check=True)
                    success = True
                except subprocess.CalledProcessError as e:
                    self.show_notification("Error", f"Failed to apply IP: {e}", "error")
                
            elif platform_system == "Darwin":  # macOS
                # macOS command to change IP
                import subprocess
                
                # Format the commands for macOS
                ip_cmd = f"sudo ifconfig {interface} {ip} netmask {subnet}"
                route_cmd = f"sudo route -n add default {gateway}"
                
                # Execute commands
                try:
                    subprocess.run(ip_cmd, shell=True, check=True)
                    subprocess.run("sudo route -n delete default", shell=True)
                    subprocess.run(route_cmd, shell=True, check=True)
                    success = True
                except subprocess.CalledProcessError as e:
                    self.show_notification("Error", f"Failed to apply IP: {e}", "error")
            
            else:
                self.show_notification("Error", f"Unsupported platform: {platform_system}", "error")
                return
            
            if success:
                self.show_notification("Success", "IP configuration applied successfully", "success")
                # Update the network manager
                if hasattr(self.network_manager, '_update_interfaces'):
                    self.network_manager._update_interfaces()
                
                # Update the display after a brief delay to allow interfaces to update
                self.after(2000, lambda: self.update_ip_config(interface))
            
        except Exception as e:
            self.show_notification("Error", f"Failed to apply IP configuration: {e}", "error")
    
    def get_cidr(self, subnet):
        """Convert subnet mask to CIDR notation (e.g., 255.255.255.0 to 24)"""
        try:
            import ipaddress
            subnet_obj = ipaddress.IPv4Address(subnet)
            subnet_int = int(subnet_obj)
            # Count the number of set bits (1s)
            return bin(subnet_int).count('1')
        except (ImportError, ValueError, Exception):
            # Default to /24 if conversion fails
            return 24 

    def initialize_ui(self):
        """Initialize the main UI components"""
        # Configure the grid
        self.grid_rowconfigure(0, weight=1)  # Chat area
        self.grid_rowconfigure(1, weight=0)  # Input area
        self.grid_columnconfigure(0, weight=0)  # Sidebar
        self.grid_columnconfigure(1, weight=1)  # Chat area
        
        # Setup sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, fg_color=self.colors["sidebar_bg"])
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=0, pady=0)
        self.sidebar.grid_columnconfigure(0, weight=1)
        self.sidebar.grid_rowconfigure(0, weight=0)  # Profile
        self.sidebar.grid_rowconfigure(1, weight=0)  # Users header
        self.sidebar.grid_rowconfigure(2, weight=1)  # Users list
        self.sidebar.grid_rowconfigure(3, weight=0)  # Users controls
        self.sidebar.grid_rowconfigure(4, weight=0)  # Utility buttons
        self.sidebar.grid_propagate(False)  # Prevent sidebar from resizing

        # Setup components
        self.setup_user_profile()
        self.setup_users_list()
        self.setup_chat_area()
        self.setup_input_area()
        self.setup_utility_buttons()
        self.setup_network_status()
        
        # Format the chat display
        self.format_chat_display()
        
        # Add a welcome message
        self.add_system_message("Welcome to ZTalk! You are in broadcast mode.")
        self.add_system_message("Select a user from the dropdown to send private messages.")
        
        # Start auto-refreshing users list
        self.auto_refresh_users()
        
    def ask_username(self):
        """Show a dialog to ask for username"""
        username_dialog = ctk.CTkInputDialog(
            text="Enter your username:",
            title="ZTalk Login"
        )
        new_username = username_dialog.get_input()
        
        if new_username and len(new_username) >= 2:
            self.username = new_username
            self.initialize_ui()
        else:
            self.destroy()  # Close the window if no valid username

    def on_terminal_input(self, text):
        """Handle input from the terminal widget"""
        # In a real implementation, this would send the input to the SSH connection
        print(f"Terminal input: {text}")
        
    def on_terminal_exit(self):
        """Handle terminal exit event"""
        # Go back to the chat view when the terminal is closed
        self.after(100, self.setup_chat_area)

    def toggle_dhcp_server(self):
        """Toggle the DHCP server on/off with a warning dialog"""
        new_state = self.dhcp_var.get()
        
        # If enabling DHCP, show warning dialog first
        if new_state:
            warning = CTkMessagebox(
                title="DHCP Server Warning",
                message="Enabling the DHCP server can cause network conflicts if your network already has a DHCP server.\n\n"
                        "Only enable this feature if:\n"
                        "• You're creating an ad-hoc network\n"
                        "• No other DHCP server exists on your network\n"
                        "• You have administrator rights\n\n"
                        "Are you sure you want to enable the DHCP server?",
                icon="warning",
                option_1="Cancel",
                option_2="Enable Anyway"
            )
            
            response = warning.get()
            if response != "Enable Anyway":
                # Reset the switch if user canceled
                self.dhcp_var.set(False)
                return
        
        # Apply the change by finding the main app instance
        try:
            import gc
            from main import ZTalkApp
            app_instances = [obj for obj in gc.get_objects() if isinstance(obj, ZTalkApp)]
            if app_instances:
                app = app_instances[0]
                success = app.enable_dhcp(new_state)
                
                if success:
                    status = "enabled" if new_state else "disabled"
                    self.show_notification("DHCP Server", f"DHCP server {status} successfully", "info")
                    self.add_system_message(f"DHCP server {status}")
                else:
                    self.show_notification("Error", "Failed to change DHCP server state", "error")
                    # Reset the switch to match actual state
                    dhcp_status = app.get_dhcp_status()
                    self.dhcp_var.set(dhcp_status.get("enabled", False))
            else:
                self.show_notification("Error", "Could not access application instance", "error")
                self.dhcp_var.set(False)
        except Exception as e:
            self.show_notification("Error", f"Failed to toggle DHCP server: {e}", "error")
            self.dhcp_var.set(False)
    
    def show_dhcp_settings(self):
        """Show DHCP server configuration dialog"""
        # Get current DHCP configuration
        dhcp_network = "192.168.100.0/24"
        dhcp_server_ip = None
        
        try:
            import gc
            from main import ZTalkApp
            app_instances = [obj for obj in gc.get_objects() if isinstance(obj, ZTalkApp)]
            if app_instances:
                app = app_instances[0]
                dhcp_status = app.get_dhcp_status()
                dhcp_network = dhcp_status.get("network", dhcp_network)
                dhcp_server_ip = dhcp_status.get("server_ip", "")
        except Exception:
            pass
        
        # Create a dialog window
        dialog = ctk.CTkToplevel(self)
        dialog.title("DHCP Server Configuration")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.focus_set()
        dialog.grab_set()
        
        # Make dialog modal
        dialog.transient(self)
        
        # Center dialog on parent window
        x = self.winfo_x() + (self.winfo_width() // 2) - (500 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (400 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Dialog content
        main_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title and warning
        title_label = ctk.CTkLabel(main_frame, 
                                 text="DHCP Server Configuration",
                                 font=ctk.CTkFont(size=18, weight="bold"),
                                 text_color=self.colors["text_light"])
        title_label.pack(pady=(0, 10))
        
        warning_text = ("⚠️ WARNING: Enabling a DHCP server on your network can cause conflicts with existing "
                      "DHCP servers and potentially disrupt network connectivity for other devices. "
                      "Only use this feature in controlled environments or when creating ad-hoc networks.")
        
        warning_label = ctk.CTkLabel(main_frame, 
                                   text=warning_text,
                                   font=ctk.CTkFont(size=12, slant="italic"),
                                   text_color="#FFD700",
                                   wraplength=460)
        warning_label.pack(pady=(0, 15))
        
        # Network settings
        settings_frame = ctk.CTkFrame(main_frame, fg_color=self.colors["chat_bg"])
        settings_frame.pack(fill="x", pady=(0, 15), ipady=10)
        
        # Network range
        network_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        network_frame.pack(fill="x", padx=15, pady=5)
        
        network_label = ctk.CTkLabel(network_frame, 
                                   text="Network CIDR:",
                                   width=120,
                                   anchor="w",
                                   font=ctk.CTkFont(size=13),
                                   text_color=self.colors["text_gray"])
        network_label.pack(side="left")
        
        network_var = tk.StringVar(value=dhcp_network)
        network_entry = ctk.CTkEntry(network_frame,
                                   textvariable=network_var,
                                   width=200,
                                   border_color=self.colors["accent"],
                                   fg_color=self.colors["input_bg"])
        network_entry.pack(side="right")
        
        # Example label
        example_label = ctk.CTkLabel(settings_frame, 
                                   text="Example: 192.168.100.0/24 (creates a network with 254 available IPs)",
                                   font=ctk.CTkFont(size=12, slant="italic"),
                                   text_color=self.colors["text_gray"])
        example_label.pack(padx=15, anchor="w")
        
        # Server IP settings
        server_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        server_frame.pack(fill="x", padx=15, pady=5)
        
        server_label = ctk.CTkLabel(server_frame, 
                                  text="Server IP:",
                                  width=120,
                                  anchor="w",
                                  font=ctk.CTkFont(size=13),
                                  text_color=self.colors["text_gray"])
        server_label.pack(side="left")
        
        server_var = tk.StringVar(value=dhcp_server_ip or "")
        server_entry = ctk.CTkEntry(server_frame,
                                  textvariable=server_var,
                                  width=200,
                                  border_color=self.colors["accent"],
                                  fg_color=self.colors["input_bg"])
        server_entry.pack(side="right")
        
        # Server IP explanation
        server_info_label = ctk.CTkLabel(settings_frame, 
                                      text="Leave blank to use first IP in the network (e.g., 192.168.100.1)",
                                      font=ctk.CTkFont(size=12, slant="italic"),
                                      text_color=self.colors["text_gray"])
        server_info_label.pack(padx=15, anchor="w")
        
        # Explanation about current status
        status_label = ctk.CTkLabel(main_frame, 
                                  text="Current DHCP Status: " + 
                                      ("Enabled" if self.dhcp_var.get() else "Disabled"),
                                  font=ctk.CTkFont(size=13),
                                  text_color=self.colors["text_light"])
        status_label.pack(pady=10)
        
        def apply_settings():
            """Apply DHCP settings"""
            network = network_var.get().strip()
            server_ip = server_var.get().strip() or None
            
            # Validate network CIDR format
            try:
                ipaddress.IPv4Network(network)
            except ValueError:
                self.show_notification("Error", "Invalid network CIDR format", "error")
                return
                
            # Validate server IP if provided
            if server_ip:
                try:
                    ipaddress.IPv4Address(server_ip)
                except ValueError:
                    self.show_notification("Error", "Invalid server IP address", "error")
                    return
            
            # Apply settings
            try:
                import gc
                from main import ZTalkApp
                app_instances = [obj for obj in gc.get_objects() if isinstance(obj, ZTalkApp)]
                if app_instances:
                    app = app_instances[0]
                    # Keep current enable/disable state, just update network settings
                    current_state = app.dhcp_enabled
                    success = app.enable_dhcp(current_state, network, server_ip)
                    
                    if success:
                        self.show_notification("Success", "DHCP settings updated", "success")
                        self.add_system_message(f"DHCP server settings updated: {network}")
                    else:
                        self.show_notification("Error", "Failed to update DHCP settings", "error")
                else:
                    self.show_notification("Error", "Could not access application instance", "error")
            except Exception as e:
                self.show_notification("Error", f"Failed to update DHCP settings: {e}", "error")
                
            # Close dialog
            dialog.destroy()
            
        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=10)
        
        # Cancel button
        cancel_button = ctk.CTkButton(button_frame,
                                    text="Cancel",
                                    command=dialog.destroy,
                                    width=100,
                                    height=35,
                                    fg_color=self.colors["button_bg"],
                                    hover_color=self.colors["button_hover"],
                                    font=ctk.CTkFont(size=13))
        cancel_button.pack(side="left", padx=10)
        
        # Apply button
        apply_button = ctk.CTkButton(button_frame,
                                   text="Apply Settings",
                                   command=apply_settings,
                                   width=150,
                                   height=35,
                                   fg_color=self.colors["accent"],
                                   hover_color=self.colors["accent_hover"],
                                   font=ctk.CTkFont(size=13, weight="bold"))
        apply_button.pack(side="right", padx=10)