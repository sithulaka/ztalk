#!/usr/bin/env python3
"""
ZTalk Demo Application

This example demonstrates a complete ZTalk application combining both
peer discovery, messaging, and SSH connection management in a single interface.
"""

import os
import sys
import time
import logging
import argparse
import threading
from typing import Dict, List, Optional, Tuple, Any

# Add parent directory to path to import ZTalk packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import ZTalkApp
from core.peer_discovery import ZTalkPeer
from core.messaging import Message, MessageType
from core.ssh_manager import SSHConnectionStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('ztalk_demo')

class ZTalkDemo:
    """
    A comprehensive demo of the ZTalk application functionality.
    Combines chat and SSH features in a single command-line interface.
    """
    
    def __init__(self, username: str):
        # Create ZTalk application
        self.app = ZTalkApp()
        self.app.set_username(username)
        
        # Register event handlers
        self.app.add_peer_listener(self._on_peer_event)
        self.app.add_message_listener(self._on_message)
        self.app.add_network_listener(self._on_network_change)
        self.app.add_ssh_listener(self._on_ssh_connection_status_change)
        
        # Track connected peers
        self.active_peers: Dict[str, ZTalkPeer] = {}
        
        # Track SSH connections
        self.ssh_connections: Dict[str, Any] = {}
        
        # Input thread
        self.running = False
        self.input_thread = None
        
        # Current mode (chat or ssh)
        self.mode = "chat"
        
    def start(self):
        """Start the ZTalk demo application"""
        # Start ZTalk application
        if not self.app.start():
            logger.error("Failed to start ZTalk application")
            return False
            
        # Start input thread
        self.running = True
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
        
        print(f"ZTalk Demo started with username: {self.app.username}")
        print("Searching for peers on the local network...")
        print("You are in CHAT mode. Type /help for available commands")
        
        # Wait for the input thread to finish
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nExiting...")
            self.running = False
            
        return True
    
    def stop(self):
        """Stop the ZTalk demo application"""
        self.running = False
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=1.0)
            
        # Close all SSH connections
        for conn_id in list(self.ssh_connections.keys()):
            self.app.close_ssh_connection(conn_id)
            
        self.app.stop()
        print("ZTalk Demo stopped")
    
    def _input_loop(self):
        """Handle user input"""
        while self.running:
            try:
                # Show different prompt based on mode
                if self.mode == "chat":
                    prompt = "chat> "
                else:
                    prompt = "ssh> "
                    
                user_input = input(prompt)
                
                if not user_input:
                    continue
                    
                # Handle commands
                if user_input.startswith('/'):
                    self._handle_command(user_input)
                elif self.mode == "chat":
                    # In chat mode, non-command input is broadcast to all peers
                    self._send_broadcast(user_input)
                else:
                    # In SSH mode, commands are invalid
                    print("Unknown command in SSH mode. Type /help for available commands")
                    
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
        parts = command.split(maxsplit=2)
        cmd = parts[0].lower()
        
        # Commands available in both modes
        if cmd == '/help':
            self._show_help()
            
        elif cmd == '/quit' or cmd == '/exit':
            print("Exiting...")
            self.running = False
            
        elif cmd == '/mode':
            if len(parts) > 1:
                new_mode = parts[1].lower()
                if new_mode in ["chat", "ssh"]:
                    self.mode = new_mode
                    print(f"Switched to {self.mode.upper()} mode")
                else:
                    print(f"Unknown mode: {new_mode}")
            else:
                print(f"Current mode: {self.mode.upper()}")
        
        # Chat mode commands
        elif self.mode == "chat":
            if cmd == '/list':
                self._list_peers()
                
            elif cmd == '/msg' and len(parts) >= 3:
                # Private message: /msg <peer_id> <message>
                peer_id = parts[1]
                message = parts[2]
                self._send_private_message(peer_id, message)
                
            elif cmd == '/create' and len(parts) >= 2:
                # Create group: /create <group_name>
                group_name = parts[1]
                group_id = self.app.create_group(group_name)
                print(f"Created group {group_name} with ID: {group_id}")
                
            elif cmd == '/join' and len(parts) >= 3:
                # Join group: /join <group_id> <peer_id>
                group_id = parts[1]
                peer_id = parts[2]
                
                if self.app.add_to_group(group_id, peer_id):
                    print(f"Added peer {peer_id} to group {group_id}")
                else:
                    print(f"Failed to add peer to group")
                    
            elif cmd == '/group' and len(parts) >= 3:
                # Group message: /group <group_id> <message>
                group_id = parts[1]
                message = parts[2]
                
                msg_id = self.app.send_message(content=message, group_id=group_id)
                if msg_id:
                    print(f"Sent message to group {group_id}")
                else:
                    print("Failed to send group message")
            
            else:
                print("Unknown command. Type /help for available commands")
                
        # SSH mode commands
        elif self.mode == "ssh":
            if cmd == '/connect':
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
        print("  /help           - Show this help message")
        print("  /mode [chat|ssh] - Show or switch the current mode")
        print("  /quit           - Exit the application")
        
        if self.mode == "chat":
            print("\nCHAT Mode Commands:")
            print("  /list                 - List active peers")
            print("  /msg <peer_id> <msg>  - Send private message to a peer")
            print("  /create <name>        - Create a new group")
            print("  /join <group> <peer>  - Add a peer to a group")
            print("  /group <group> <msg>  - Send message to a group")
            print("  (any other text)      - Send broadcast message to all peers")
        else:  # SSH mode
            print("\nSSH Mode Commands:")
            print("  /connect         - Connect to a new SSH server (interactive)")
            print("  /list            - List active SSH connections")
            print("  /close <id>      - Close an active SSH connection")
            print("  /profiles        - List saved SSH profiles")
            print("  /load <name>     - Connect using a saved profile")
            print("  /delete_profile <name> - Delete a saved profile")
            
        print("")
    
    # Chat-related methods
    
    def _list_peers(self):
        """List active peers"""
        peers = self.app.get_active_peers()
        if not peers:
            print("No active peers found")
            return
            
        print("\nActive peers:")
        for peer in peers:
            print(f"  {peer.name} ({peer.peer_id})")
        print("")
    
    def _send_broadcast(self, message: str):
        """Send a broadcast message to all peers"""
        msg_id = self.app.broadcast_message(message)
        if not msg_id:
            print("Failed to send broadcast message")
    
    def _send_private_message(self, peer_id: str, message: str):
        """Send a private message to a specific peer"""
        msg_id = self.app.send_message(content=message, peer_id=peer_id)
        if not msg_id:
            print(f"Failed to send message to peer {peer_id}")
    
    # SSH-related methods
    
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
            self.ssh_connections[conn_id] = self.app.get_ssh_connection(conn_id)
            
            # Save profile if requested
            if save_profile and profile_name:
                if self.app.save_ssh_profile(
                    name=profile_name,
                    host=host,
                    port=port,
                    username=username,
                    key_path=key_path
                ):
                    print(f"Profile '{profile_name}' saved")
                else:
                    print(f"Failed to save profile '{profile_name}'")
        else:
            print("Failed to create SSH connection")
    
    def _list_connections(self):
        """List active SSH connections"""
        connections = self.app.get_all_ssh_connections()
        if not connections:
            print("No active SSH connections")
            return
            
        print("\nActive SSH connections:")
        for conn in connections:
            status_str = "Connected" if conn.status == SSHConnectionStatus.CONNECTED else str(conn.status.name)
            print(f"  {conn.connection_id}: {conn.username}@{conn.host}:{conn.port} - {status_str}")
        print("")
    
    def _close_connection(self, conn_id: str):
        """Close an active SSH connection"""
        connection = self.app.get_ssh_connection(conn_id)
        if not connection:
            print(f"Connection not found: {conn_id}")
            return
            
        if self.app.close_ssh_connection(conn_id):
            print(f"Connection closed: {conn_id}")
            if conn_id in self.ssh_connections:
                del self.ssh_connections[conn_id]
        else:
            print(f"Failed to close connection: {conn_id}")
    
    def _list_profiles(self):
        """List saved SSH profiles"""
        profiles = self.app.get_all_ssh_profiles()
        if not profiles:
            print("No saved SSH profiles")
            return
            
        print("\nSaved SSH profiles:")
        for profile_id, profile in profiles.items():
            auth_type = "Key" if profile.get("key_path") else "Password"
            print(f"  {profile.get('name')}: {profile.get('username')}@{profile.get('host')}:{profile.get('port')} ({auth_type})")
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
            self.ssh_connections[conn_id] = self.app.get_ssh_connection(conn_id)
        else:
            print(f"Failed to connect using profile '{profile_name}'")
    
    # Event handlers
    
    def _on_peer_event(self, event_type: str, peer: ZTalkPeer):
        """Handle peer discovery events"""
        if event_type == "added":
            self.active_peers[peer.peer_id] = peer
            print(f"\nPeer discovered: {peer.name} ({peer.peer_id})")
            if self.mode == "chat":
                print("chat> ", end='', flush=True)
            else:
                print("ssh> ", end='', flush=True)
            
        elif event_type == "removed":
            if peer.peer_id in self.active_peers:
                del self.active_peers[peer.peer_id]
                print(f"\nPeer lost: {peer.name} ({peer.peer_id})")
                if self.mode == "chat":
                    print("chat> ", end='', flush=True)
                else:
                    print("ssh> ", end='', flush=True)
    
    def _on_message(self, message: Message):
        """Handle incoming messages"""
        # Skip our own messages
        if message.sender_id == self.app.peer_discovery.instance_id:
            return
            
        # Format and display the message
        if message.msg_type == MessageType.CHAT:
            if message.group_id:
                # Group message
                print(f"\n[Group {message.group_id}] {message.sender_name}: {message.content}")
            elif message.recipient_id:
                # Private message
                print(f"\n[Private] {message.sender_name}: {message.content}")
            else:
                # Broadcast message
                print(f"\n{message.sender_name}: {message.content}")
                
            # Reprint the prompt
            if self.mode == "chat":
                print("chat> ", end='', flush=True)
            else:
                print("ssh> ", end='', flush=True)
    
    def _on_network_change(self, new_interfaces: Dict[str, str], old_interfaces: Dict[str, str]):
        """Handle network interface changes"""
        if new_interfaces:
            ips = list(new_interfaces.values())
            print(f"\nNetwork interfaces changed. Active IPs: {ips}")
            if self.mode == "chat":
                print("chat> ", end='', flush=True)
            else:
                print("ssh> ", end='', flush=True)
    
    def _on_ssh_connection_status_change(self, event_type: str, connection: Any):
        """Handle SSH connection status changes"""
        conn_id = connection.connection_id
        status = connection.status
        
        # Update connection in our local tracking
        self.ssh_connections[conn_id] = connection
        
        # Print status change
        if status == SSHConnectionStatus.CONNECTED:
            print(f"\nSSH connection established: {connection.username}@{connection.host}")
        elif status == SSHConnectionStatus.DISCONNECTED:
            print(f"\nSSH connection closed: {connection.username}@{connection.host}")
            # Remove from tracking
            if conn_id in self.ssh_connections:
                del self.ssh_connections[conn_id]
        elif status == SSHConnectionStatus.ERROR:
            print(f"\nSSH connection error: {connection.username}@{connection.host} - {connection.error_message}")
        
        # Reprint prompt
        if self.mode == "chat":
            print("chat> ", end='', flush=True)
        else:
            print("ssh> ", end='', flush=True)


def main():
    """Main entry point for the ZTalk demo"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ZTalk Demo Application")
    parser.add_argument('--username', type=str, help='Display name')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get username
    username = args.username
    if not username:
        # Prompt for username
        username = input("Enter your username: ")
        if not username:
            print("Username is required")
            return 1
    
    # Create and start the demo application
    demo = ZTalkDemo(username)
    try:
        if not demo.start():
            return 1
    finally:
        demo.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 