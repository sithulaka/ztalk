import customtkinter as ctk
import tkinter as tk
import threading
import time
import os
import platform
import subprocess
import json
import socket
import sys
from typing import Dict, List, Optional, Callable, Tuple
from .terminal_widget import TerminalWidget
from utils.ssh_utils import check_ssh_client_installed, install_ssh_client, get_default_ssh_key_path, generate_ssh_key

class SSHClient(ctk.CTkToplevel):
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title("ZTalk SSH Client")
        self.geometry("900x600")
        self.minsize(800, 500)
        
        # Platform-specific configurations
        self.platform = platform.system()
        self.setup_platform_specifics()
        
        # SSH connections and settings
        self.connections: Dict[str, Dict] = {}  # {connection_name: {host, port, username, key_path, terminal}}
        self.active_connection: Optional[str] = None
        self.saved_profiles: Dict[str, Dict] = {}
        
        # Check if ssh is installed
        self.check_ssh_installed()
        
        # Create main layout
        self.setup_ui()
        
        # Load saved profiles
        self.load_profiles()
        
        # Center the window on screen
        self.center_window()
        
        # Used to track terminal input/output
        self.buffer_lock = threading.Lock()
        self.output_buffers: Dict[str, List[str]] = {}
        
    def setup_platform_specifics(self):
        """Configure platform-specific settings"""
        if self.platform == "Windows":
            self.protocol("WM_DELETE_WINDOW", self.on_close)
            # On Windows, we might need to use PuTTY or similar
            self.ssh_command = "ssh"  # Will check if available
        elif self.platform == "Darwin":  # macOS
            self.createcommand('exit', self.on_close)
            self.ssh_command = "ssh"
        else:  # Linux
            self.protocol("WM_DELETE_WINDOW", self.on_close)
            self.ssh_command = "ssh"
            
    def check_ssh_installed(self):
        """Check if SSH client is installed"""
        installed, path_or_msg = check_ssh_client_installed()
        
        if not installed:
            self.after(500, lambda: self.show_error_message(
                f"SSH client not installed: {path_or_msg}\n\n"
                "Would you like to install it?"
            ))
            
            success, msg = install_ssh_client()
            if success:
                self.after(500, lambda: self.show_info_message(
                    f"SSH client installed: {msg}"
                ))
            else:
                self.after(500, lambda: self.show_error_message(
                    f"Could not install SSH client: {msg}"
                ))
        
        return installed
            
    def setup_ui(self):
        """Set up the main user interface"""
        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header with connection controls
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        # Connection profile selector
        self.profile_var = ctk.StringVar(value="Select profile")
        self.profile_dropdown = ctk.CTkComboBox(
            self.header_frame, 
            values=["Select profile"], 
            variable=self.profile_var,
            command=self.on_profile_selected,
            width=200
        )
        self.profile_dropdown.pack(side="left", padx=(10, 5), pady=10)
        
        # Quick connect button
        self.connect_btn = ctk.CTkButton(
            self.header_frame, 
            text="Quick Connect", 
            command=self.show_connect_dialog
        )
        self.connect_btn.pack(side="left", padx=5, pady=10)
        
        # Save profile button
        self.save_btn = ctk.CTkButton(
            self.header_frame, 
            text="Save Profile",
            command=self.show_save_profile_dialog
        )
        self.save_btn.pack(side="left", padx=5, pady=10)
        
        # Disconnect button
        self.disconnect_btn = ctk.CTkButton(
            self.header_frame,
            text="Disconnect",
            command=self.disconnect_current,
            fg_color="darkred",
            state="disabled"
        )
        self.disconnect_btn.pack(side="right", padx=10, pady=10)
        
        # Tab view for multiple SSH connections
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.tab_view.add("Welcome")
        
        # Welcome tab content
        welcome_text = (
            "SSH Client\n\n"
            "Use the controls above to connect to SSH servers.\n"
            "You can save connection profiles for quick access.\n\n"
            "Quick Connect: Connect to a server by entering details\n"
            "Save Profile: Save current connection settings\n"
            "Disconnect: Close the current connection\n\n"
            "Each connection will open in a new tab."
        )
        welcome_label = ctk.CTkLabel(
            self.tab_view.tab("Welcome"),
            text=welcome_text,
            font=ctk.CTkFont(size=14),
            justify="left"
        )
        welcome_label.pack(padx=20, pady=20)
        
        # Status bar
        self.status_bar = ctk.CTkFrame(self, height=25)
        self.status_bar.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        self.status_label = ctk.CTkLabel(self.status_bar, text="Ready", anchor="w")
        self.status_label.pack(side="left", padx=10)
        
    def center_window(self):
        """Center the window on the screen"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')
        
    def load_profiles(self):
        """Load saved SSH profiles"""
        profiles_file = os.path.expanduser("~/.ztalk/ssh_profiles.json")
        
        try:
            if os.path.exists(profiles_file):
                with open(profiles_file, 'r') as f:
                    self.saved_profiles = json.load(f)
                    
                # Update profile dropdown
                profile_names = list(self.saved_profiles.keys())
                if profile_names:
                    self.profile_dropdown.configure(values=["Select profile"] + profile_names)
        except Exception as e:
            print(f"Error loading profiles: {e}")
            
    def save_profiles(self):
        """Save SSH profiles to file"""
        profiles_dir = os.path.expanduser("~/.ztalk")
        profiles_file = os.path.join(profiles_dir, "ssh_profiles.json")
        
        try:
            # Ensure directory exists
            os.makedirs(profiles_dir, exist_ok=True)
            
            with open(profiles_file, 'w') as f:
                json.dump(self.saved_profiles, f)
        except Exception as e:
            print(f"Error saving profiles: {e}")
            
    def show_connect_dialog(self):
        """Show dialog to enter connection details"""
        connect_dialog = ctk.CTkToplevel(self)
        connect_dialog.title("SSH Connection")
        connect_dialog.geometry("400x350")
        connect_dialog.resizable(False, False)
        connect_dialog.grab_set()
        
        # Center the dialog
        connect_dialog.update_idletasks()
        width = connect_dialog.winfo_width()
        height = connect_dialog.winfo_height()
        x = (connect_dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (connect_dialog.winfo_screenheight() // 2) - (height // 2)
        connect_dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # Connection form
        ctk.CTkLabel(connect_dialog, text="Connection Name:").grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        name_entry = ctk.CTkEntry(connect_dialog, width=250)
        name_entry.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="w")
        
        ctk.CTkLabel(connect_dialog, text="Host:").grid(row=1, column=0, padx=20, pady=5, sticky="w")
        host_entry = ctk.CTkEntry(connect_dialog, width=250)
        host_entry.grid(row=1, column=1, padx=20, pady=5, sticky="w")
        
        ctk.CTkLabel(connect_dialog, text="Port:").grid(row=2, column=0, padx=20, pady=5, sticky="w")
        port_entry = ctk.CTkEntry(connect_dialog, width=250)
        port_entry.insert(0, "22")
        port_entry.grid(row=2, column=1, padx=20, pady=5, sticky="w")
        
        ctk.CTkLabel(connect_dialog, text="Username:").grid(row=3, column=0, padx=20, pady=5, sticky="w")
        username_entry = ctk.CTkEntry(connect_dialog, width=250)
        username_entry.grid(row=3, column=1, padx=20, pady=5, sticky="w")
        
        ctk.CTkLabel(connect_dialog, text="Key File (optional):").grid(row=4, column=0, padx=20, pady=5, sticky="w")
        key_frame = ctk.CTkFrame(connect_dialog, fg_color="transparent")
        key_frame.grid(row=4, column=1, padx=20, pady=5, sticky="w")
        
        key_entry = ctk.CTkEntry(key_frame, width=200)
        key_entry.pack(side="left")
        
        def browse_key():
            filename = tk.filedialog.askopenfilename(
                title="Select SSH Key",
                filetypes=[("All Files", "*.*")]
            )
            if filename:
                key_entry.delete(0, tk.END)
                key_entry.insert(0, filename)
                
        browse_btn = ctk.CTkButton(key_frame, text="Browse", width=40, command=browse_key)
        browse_btn.pack(side="right", padx=5)
        
        # Network selection for routing (using the network segments)
        ctk.CTkLabel(connect_dialog, text="Network Interface:").grid(row=5, column=0, padx=20, pady=5, sticky="w")
        network_var = ctk.StringVar(value="Auto")
        network_dropdown = ctk.CTkComboBox(
            connect_dialog,
            values=["Auto"],
            variable=network_var,
            width=250
        )
        network_dropdown.grid(row=5, column=1, padx=20, pady=5, sticky="w")
        
        # Buttons
        btn_frame = ctk.CTkFrame(connect_dialog, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        def on_connect():
            name = name_entry.get().strip()
            host = host_entry.get().strip()
            port = port_entry.get().strip()
            username = username_entry.get().strip()
            key_path = key_entry.get().strip()
            
            if not name:
                name = f"{username}@{host}"
                
            if not host:
                self.show_error_message("Host is required")
                return
                
            try:
                port = int(port)
            except ValueError:
                self.show_error_message("Port must be a number")
                return
                
            if not username:
                self.show_error_message("Username is required")
                return
                
            # Create connection
            connect_dialog.destroy()
            self.connect_ssh(name, host, port, username, key_path)
        
        connect_btn = ctk.CTkButton(btn_frame, text="Connect", command=on_connect)
        connect_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            fg_color="transparent", 
            command=connect_dialog.destroy
        )
        cancel_btn.pack(side="right", padx=10)
        
    def show_save_profile_dialog(self):
        """Show dialog to save current connection as a profile"""
        if not self.active_connection:
            self.show_error_message("No active connection to save")
            return
            
        save_dialog = ctk.CTkToplevel(self)
        save_dialog.title("Save SSH Profile")
        save_dialog.geometry("400x200")
        save_dialog.resizable(False, False)
        save_dialog.grab_set()
        
        # Center the dialog
        save_dialog.update_idletasks()
        width = save_dialog.winfo_width()
        height = save_dialog.winfo_height()
        x = (save_dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (save_dialog.winfo_screenheight() // 2) - (height // 2)
        save_dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # Connection info
        conn = self.connections[self.active_connection]
        
        # Profile name
        ctk.CTkLabel(save_dialog, text="Profile Name:").grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        name_entry = ctk.CTkEntry(save_dialog, width=250)
        name_entry.insert(0, self.active_connection)
        name_entry.grid(row=0, column=1, padx=20, pady=(20, 5), sticky="w")
        
        # Connection details (display only)
        details_text = f"Host: {conn['host']}\nPort: {conn['port']}\nUsername: {conn['username']}"
        if conn.get('key_path'):
            details_text += f"\nKey: {conn['key_path']}"
            
        ctk.CTkLabel(save_dialog, text="Connection Details:").grid(row=1, column=0, padx=20, pady=5, sticky="nw")
        ctk.CTkLabel(save_dialog, text=details_text, justify="left").grid(row=1, column=1, padx=20, pady=5, sticky="w")
        
        # Buttons
        btn_frame = ctk.CTkFrame(save_dialog, fg_color="transparent")
        btn_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        def on_save():
            name = name_entry.get().strip()
            
            if not name:
                self.show_error_message("Profile name is required")
                return
                
            # Save profile
            self.saved_profiles[name] = {
                'host': conn['host'],
                'port': conn['port'],
                'username': conn['username'],
                'key_path': conn.get('key_path', '')
            }
            
            # Update dropdown
            profile_names = list(self.saved_profiles.keys())
            self.profile_dropdown.configure(values=["Select profile"] + profile_names)
            
            # Save to file
            self.save_profiles()
            
            save_dialog.destroy()
            self.show_info_message(f"Profile '{name}' saved")
        
        save_btn = ctk.CTkButton(btn_frame, text="Save", command=on_save)
        save_btn.pack(side="left", padx=10)
        
        cancel_btn = ctk.CTkButton(
            btn_frame, 
            text="Cancel", 
            fg_color="transparent", 
            command=save_dialog.destroy
        )
        cancel_btn.pack(side="right", padx=10)
        
    def on_profile_selected(self, profile_name):
        """Handle profile selection from dropdown"""
        if profile_name == "Select profile":
            return
            
        # Get profile
        profile = self.saved_profiles.get(profile_name)
        if not profile:
            return
            
        # Connect using profile
        self.connect_ssh(
            profile_name,
            profile['host'],
            profile['port'],
            profile['username'],
            profile.get('key_path', '')
        )
        
    def connect_ssh(self, name, host, port, username, key_path=None):
        """Connect to SSH server"""
        # Check if connection with this name already exists
        if name in self.connections:
            # If it exists, just switch to that tab
            self.tab_view.set(name)
            return
            
        # Update status
        self.set_status(f"Connecting to {username}@{host}:{port}...")
        
        # Create a new tab
        self.tab_view.add(name)
        terminal_frame = self.tab_view.tab(name)
        
        # Create terminal widget
        terminal = TerminalWidget(terminal_frame)
        terminal.pack(fill="both", expand=True)
        
        # Store connection info
        self.connections[name] = {
            'host': host,
            'port': port,
            'username': username,
            'key_path': key_path,
            'terminal': terminal,
            'process': None,
            'connected': False
        }
        
        # Initialize buffer
        self.output_buffers[name] = []
        
        # Switch to new tab
        self.tab_view.set(name)
        self.active_connection = name
        
        # Enable disconnect button
        self.disconnect_btn.configure(state="normal")
        
        # Start SSH connection in a thread
        threading.Thread(target=self._connect_ssh_thread, args=(name,), daemon=True).start()
        
    def _connect_ssh_thread(self, connection_name):
        """Thread function for SSH connection"""
        conn = self.connections.get(connection_name)
        if not conn:
            return
            
        try:
            # Build SSH command
            cmd = [self.ssh_command]
            
            # Add port
            cmd.extend(['-p', str(conn['port'])])
            
            # Add key if provided
            if conn.get('key_path'):
                cmd.extend(['-i', conn['key_path']])
                
            # Add target
            cmd.append(f"{conn['username']}@{conn['host']}")
            
            # Start process
            if self.platform == "Windows":
                from subprocess import CREATE_NEW_PROCESS_GROUP
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=CREATE_NEW_PROCESS_GROUP
                )
            else:
                process = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
            # Store process
            conn['process'] = process
            conn['connected'] = True
            
            # Start read threads
            threading.Thread(target=self._read_stdout, args=(connection_name,), daemon=True).start()
            threading.Thread(target=self._read_stderr, args=(connection_name,), daemon=True).start()
            
            # Update UI
            self.after(100, lambda: self.set_status(f"Connected to {conn['username']}@{conn['host']}:{conn['port']}"))
            
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            self.after(100, lambda: self.set_status(error_msg))
            self.after(100, lambda: self.show_error_message(error_msg))
            
            # Update terminal
            with self.buffer_lock:
                self.output_buffers[connection_name].append(f"Error: {error_msg}\n")
                
            # Update terminal UI
            self.after(100, lambda: self._update_terminal(connection_name))
            
    def _read_stdout(self, connection_name):
        """Read stdout from SSH process"""
        conn = self.connections.get(connection_name)
        if not conn or not conn.get('process'):
            return
            
        process = conn['process']
        
        while conn.get('connected', False):
            try:
                line = process.stdout.readline()
                if not line:
                    break
                    
                # Add to buffer
                with self.buffer_lock:
                    self.output_buffers[connection_name].append(line)
                    
                # Update terminal UI
                self.after(10, lambda: self._update_terminal(connection_name))
                
            except Exception as e:
                print(f"Error reading stdout: {e}")
                break
                
        # Process has ended
        if connection_name in self.connections:
            self.connections[connection_name]['connected'] = False
            
    def _read_stderr(self, connection_name):
        """Read stderr from SSH process"""
        conn = self.connections.get(connection_name)
        if not conn or not conn.get('process'):
            return
            
        process = conn['process']
        
        while conn.get('connected', False):
            try:
                line = process.stderr.readline()
                if not line:
                    break
                    
                # Add to buffer
                with self.buffer_lock:
                    self.output_buffers[connection_name].append(f"ERROR: {line}")
                    
                # Update terminal UI
                self.after(10, lambda: self._update_terminal(connection_name))
                
            except Exception as e:
                print(f"Error reading stderr: {e}")
                break
                
    def _update_terminal(self, connection_name):
        """Update terminal widget with buffered output"""
        conn = self.connections.get(connection_name)
        if not conn or not conn.get('terminal'):
            return
            
        terminal = conn['terminal']
        
        # Get buffer content
        lines = []
        with self.buffer_lock:
            lines = self.output_buffers[connection_name].copy()
            self.output_buffers[connection_name] = []
            
        # Update terminal
        for line in lines:
            terminal.append_text(line)
            
    def send_command(self, connection_name, command):
        """Send command to SSH process"""
        conn = self.connections.get(connection_name)
        if not conn or not conn.get('process') or not conn.get('connected'):
            return
            
        process = conn['process']
        
        try:
            # Add newline if not present
            if not command.endswith('\n'):
                command += '\n'
                
            # Send command
            process.stdin.write(command)
            process.stdin.flush()
            
        except Exception as e:
            print(f"Error sending command: {e}")
            
    def disconnect_current(self):
        """Disconnect current SSH connection"""
        if not self.active_connection:
            return
            
        conn = self.connections.get(self.active_connection)
        if not conn:
            return
            
        # Kill process
        if conn.get('process'):
            try:
                conn['process'].terminate()
            except:
                pass
                
        # Mark as disconnected
        conn['connected'] = False
        
        # Update UI
        self.set_status(f"Disconnected from {conn['username']}@{conn['host']}")
        
        # Remove tab
        self.tab_view.delete(self.active_connection)
        del self.connections[self.active_connection]
        
        # Update active connection
        self.active_connection = None
        
        # Disable disconnect button if no connections left
        if not self.connections:
            self.disconnect_btn.configure(state="disabled")
            
    def on_close(self):
        """Handle window closing"""
        # Disconnect all connections
        for name, conn in list(self.connections.items()):
            if conn.get('process'):
                try:
                    conn['process'].terminate()
                except:
                    pass
                    
        # Destroy window
        self.destroy()
        
    def set_status(self, message):
        """Update status bar message"""
        self.status_label.configure(text=message)
        
    def show_error_message(self, message):
        """Show error message dialog"""
        from tkinter import messagebox
        messagebox.showerror("Error", message)
        
    def show_info_message(self, message):
        """Show info message dialog"""
        from tkinter import messagebox
        messagebox.showinfo("Information", message) 