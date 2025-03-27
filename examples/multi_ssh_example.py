#!/usr/bin/env python3
"""
ZTalk Multi-SSH Example

This example demonstrates how to manage multiple SSH connections using ZTalk.
"""

import os
import sys
import time
import logging
import argparse
import threading
from typing import Dict, List, Optional

# Add parent directory to path to import ZTalk packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import ZTalkApp
from core.ssh_manager import SSHConnection, SSHConnectionStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('multi_ssh_example')

class MultiSSHExample:
    """
    Example showing how to manage multiple SSH connections.
    """
    
    def __init__(self):
        # Create ZTalk application
        self.app = ZTalkApp()
        
        # Track active connections
        self.connections: Dict[str, SSHConnection] = {}
        
        # Input thread
        self.running = False
        self.input_thread = None
    
    def start(self) -> bool:
        """Start the example application"""
        # Start ZTalk application
        if not self.app.start():
            logger.error("Failed to start ZTalk application")
            return False
            
        # Register SSH status event handler
        self.app.add_ssh_listener(self._on_ssh_connection_status_change)
        
        # Start input thread
        self.running = True
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
        
        print("ZTalk Multi-SSH Example started")
        print("Type /help for available commands")
        
        # Wait for the input thread to finish
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nExiting...")
            self.running = False
            
        return True
    
    def stop(self):
        """Stop the example application"""
        self.running = False
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=1.0)
            
        # Close all SSH connections
        for conn_id in list(self.connections.keys()):
            self.app.close_ssh_connection(conn_id)
            
        self.app.stop()
        print("Example stopped")
    
    def _input_loop(self):
        """Handle user input"""
        while self.running:
            try:
                user_input = input("> ")
                
                if not user_input:
                    continue
                    
                # Handle commands
                if user_input.startswith('/'):
                    self._handle_command(user_input)
                    
            except EOFError:
                # Ctrl+D pressed
                print("\nExiting...")
                self.running = False
                break
            except KeyboardInterrupt:
                # Ctrl+C pressed
                print("\nExiting...")
                self.running = False
                break
    
    def _handle_command(self, command: str):
        """Handle commands"""
        parts = command.split(maxsplit=1)
        cmd = parts[0].lower()
        
        if cmd == '/help':
            self._show_help()
            
        elif cmd == '/quit' or cmd == '/exit':
            print("Exiting...")
            self.running = False
            
        elif cmd == '/connect':
            self._interactive_connect()
            
        elif cmd == '/list':
            self._list_connections()
            
        elif cmd == '/close' and len(parts) > 1:
            conn_id = parts[1]
            self._close_connection(conn_id)
            
        elif cmd == '/profiles':
            self._list_profiles()
            
        elif cmd == '/delete_profile' and len(parts) > 1:
            profile_name = parts[1]
            self._delete_profile(profile_name)
            
        elif cmd == '/load' and len(parts) > 1:
            profile_name = parts[1]
            self._load_profile(profile_name)
            
        else:
            print("Unknown command. Type /help for available commands")
    
    def _show_help(self):
        """Show available commands"""
        print("\nAvailable commands:")
        print("  /help            - Show this help message")
        print("  /connect         - Connect to a new SSH server (interactive)")
        print("  /list            - List active SSH connections")
        print("  /close <id>      - Close an active SSH connection")
        print("  /profiles        - List saved SSH profiles")
        print("  /load <name>     - Connect using a saved profile")
        print("  /delete_profile <name> - Delete a saved profile")
        print("  /quit            - Exit the application")
        print("")
    
    def _interactive_connect(self):
        """Interactively connect to an SSH server"""
        print("\nConnect to SSH server:")
        
        host = input("Host: ")
        if not host:
            print("Cancelled")
            return
            
        port_str = input("Port [22]: ")
        port = int(port_str) if port_str else 22
        
        username = input("Username: ")
        if not username:
            print("Cancelled")
            return
            
        use_password = input("Use password? (y/n) [y]: ").lower() != 'n'
        
        password = None
        key_path = None
        
        if use_password:
            password = input("Password: ")
        else:
            key_path = input("Key file path: ")
            if not os.path.exists(key_path):
                print(f"Key file not found: {key_path}")
                return
        
        save_profile = input("Save as profile? (y/n) [n]: ").lower() == 'y'
        profile_name = None
        
        if save_profile:
            profile_name = input("Profile name: ")
            if not profile_name:
                print("Profile name cannot be empty, continuing without saving")
                profile_name = None
        
        # Create the connection
        conn_id = self.app.create_ssh_connection(
            host=host,
            port=port,
            username=username,
            password=password,
            key_path=key_path
        )
        
        if conn_id:
            print(f"SSH connection created with ID: {conn_id}")
            self.connections[conn_id] = self.app.get_ssh_connection(conn_id)
            
            # Save profile if requested
            if save_profile and profile_name:
                profile_id = self.app.save_ssh_profile(
                    name=profile_name,
                    host=host,
                    port=port,
                    username=username,
                    key_path=key_path
                )
                if profile_id:
                    print(f"SSH profile saved with ID: {profile_id}")
                else:
                    print("Failed to save SSH profile")
        else:
            print("Failed to create SSH connection")
    
    def _list_connections(self):
        """List active SSH connections"""
        connections = list(self.connections.values())
        if not connections:
            print("No active SSH connections")
            return
            
        print("\nActive SSH connections:")
        for conn in connections:
            status_str = "Connected" if conn.status == SSHConnectionStatus.CONNECTED else str(conn.status)
            print(f"  {conn.connection_id}: {conn.username}@{conn.host}:{conn.port} - {status_str}")
        print("")
    
    def _close_connection(self, conn_id: str):
        """Close an active SSH connection"""
        if conn_id not in self.connections:
            print(f"Connection not found: {conn_id}")
            return
            
        if self.app.close_ssh_connection(conn_id):
            print(f"Connection closed: {conn_id}")
            if conn_id in self.connections:
                del self.connections[conn_id]
        else:
            print(f"Failed to close connection: {conn_id}")
    
    def _list_profiles(self):
        """List saved SSH profiles"""
        profiles = self.app.get_all_ssh_profiles()
        if not profiles:
            print("No saved SSH profiles")
            return
            
        print("\nSaved SSH profiles:")
        for profile in profiles:
            auth_type = "Password" if profile.password else "Key"
            print(f"  {profile.name}: {profile.username}@{profile.host}:{profile.port} ({auth_type})")
        print("")
    
    def _delete_profile(self, profile_name: str):
        """Delete a saved SSH profile"""
        if self.app.delete_ssh_profile(profile_name):
            print(f"Profile deleted: {profile_name}")
        else:
            print(f"Failed to delete profile: {profile_name}")
    
    def _load_profile(self, profile_name: str):
        """Load and connect using a saved profile"""
        profile = self.app.get_ssh_profile(profile_name)
        if not profile:
            print(f"Profile not found: {profile_name}")
            return
            
        conn_id = self.app.connect_from_ssh_profile(profile_name)
        if conn_id:
            print(f"Connecting using profile '{profile_name}', connection ID: {conn_id}")
            self.connections[conn_id] = self.app.get_ssh_connection(conn_id)
        else:
            print(f"Failed to connect using profile '{profile_name}'")
    
    def _on_ssh_connection_status_change(self, connection: SSHConnection):
        """Handle SSH connection status changes"""
        conn_id = connection.connection_id
        status = connection.status
        
        # Update connection in our local tracking
        self.connections[conn_id] = connection
        
        # Print status change
        if status == SSHConnectionStatus.CONNECTED:
            print(f"\nSSH connection established: {connection.username}@{connection.host}")
        elif status == SSHConnectionStatus.DISCONNECTED:
            print(f"\nSSH connection closed: {connection.username}@{connection.host}")
            # Remove from tracking
            if conn_id in self.connections:
                del self.connections[conn_id]
        elif status == SSHConnectionStatus.ERROR:
            print(f"\nSSH connection error: {connection.username}@{connection.host} - {connection.error_message}")
        
        # Reprint prompt
        print("> ", end='', flush=True)


def main():
    """Main entry point for the multi-SSH example"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ZTalk Multi-SSH Example")
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and start the example application
    example = MultiSSHExample()
    try:
        if not example.start():
            return 1
    finally:
        example.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())