#!/usr/bin/env python3
"""
ZTalk Chat Example

This example demonstrates how to use the peer discovery and messaging systems
to create a simple chat application.
"""

import os
import sys
import time
import logging
import argparse
import threading
from typing import Dict, Any, List

# Add parent directory to path to import ZTalk packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core import ZTalkApp, ZTalkPeer, Message, MessageType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('chat_example')

class SimpleChat:
    """
    A simple chat application using ZTalk's peer discovery and messaging.
    """
    
    def __init__(self, username: str):
        # Create ZTalk application
        self.app = ZTalkApp()
        self.app.set_username(username)
        
        # Register event handlers
        self.app.add_peer_listener(self._on_peer_event)
        self.app.add_message_listener(self._on_message)
        self.app.add_network_listener(self._on_network_change)
        
        # Track peers
        self.active_peers: Dict[str, ZTalkPeer] = {}
        
        # Input thread
        self.running = False
        self.input_thread = None
        
    def start(self):
        """Start the chat application"""
        # Start ZTalk application
        if not self.app.start():
            logger.error("Failed to start ZTalk application")
            return False
            
        # Start input thread
        self.running = True
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()
        
        print(f"ZTalk Chat started with username: {self.app.username}")
        print("Searching for peers...")
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
        """Stop the chat application"""
        self.running = False
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=1.0)
            
        self.app.stop()
        print("Chat stopped")
    
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
                else:
                    # Regular message, broadcast to all peers
                    self._send_broadcast(user_input)
                    
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
        """Handle chat commands"""
        parts = command.split(maxsplit=2)
        cmd = parts[0].lower()
        
        if cmd == '/help':
            self._show_help()
            
        elif cmd == '/quit' or cmd == '/exit':
            print("Exiting...")
            self.running = False
            
        elif cmd == '/list':
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
    
    def _show_help(self):
        """Show available commands"""
        print("\nAvailable commands:")
        print("  /help                 - Show this help message")
        print("  /list                 - List active peers")
        print("  /msg <peer_id> <msg>  - Send private message to a peer")
        print("  /create <name>        - Create a new group")
        print("  /join <group> <peer>  - Add a peer to a group")
        print("  /group <group> <msg>  - Send message to a group")
        print("  /quit                 - Exit the application")
        print("")
    
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
    
    # Event handlers
    
    def _on_peer_event(self, event_type: str, peer: ZTalkPeer):
        """Handle peer discovery events"""
        if event_type == "added":
            self.active_peers[peer.peer_id] = peer
            print(f"\nPeer discovered: {peer.name} ({peer.peer_id})")
            print("> ", end='', flush=True)
            
        elif event_type == "removed":
            if peer.peer_id in self.active_peers:
                del self.active_peers[peer.peer_id]
                print(f"\nPeer lost: {peer.name} ({peer.peer_id})")
                print("> ", end='', flush=True)
    
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
            print("> ", end='', flush=True)
    
    def _on_network_change(self, new_interfaces: Dict[str, str], old_interfaces: Dict[str, str]):
        """Handle network interface changes"""
        if new_interfaces:
            ips = list(new_interfaces.values())
            print(f"\nNetwork interfaces changed. Active IPs: {ips}")
            print("> ", end='', flush=True)


def main():
    """Main entry point for the chat example"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ZTalk Chat Example")
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
    
    # Create and start the chat application
    chat = SimpleChat(username)
    try:
        if not chat.start():
            return 1
    finally:
        chat.stop()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 