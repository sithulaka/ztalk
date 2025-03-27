"""
SSH Client for ZTalk

Integrates the SSH manager with a terminal UI for interactive SSH sessions.
"""

import os
import sys
import time
import threading
import logging
from typing import Optional, Dict, List, Any, Tuple, Callable

from core.ssh_manager import SSHManager, SSHConnection, SSHConnectionStatus
from ui.terminal_widget import TerminalWidget
from ui.notification import Notification

# Configure logging
logger = logging.getLogger(__name__)

class SSHClient:
    """
    SSH Client that integrates the SSH manager with a terminal UI.
    Provides an interface for creating and managing SSH sessions.
    """
    
    def __init__(self):
        # Create SSH manager
        self.ssh_manager = SSHManager()
        self.ssh_manager.start()
        
        # Active connections
        self.active_terminals: Dict[str, Tuple[SSHConnection, TerminalWidget, threading.Thread]] = {}
        
        # Connection attempt in progress
        self.connecting: Dict[str, threading.Thread] = {}
        
        logger.info("SSH client initialized")
    
    def connect(self, host: str, port: int = 22, username: str = "", 
               password: Optional[str] = None, key_path: Optional[str] = None,
               name: Optional[str] = None) -> Optional[str]:
        """
        Connect to an SSH server.
        Returns the connection ID if successful, None otherwise.
        """
        # Create a more descriptive name if none provided
        if not name:
            name = f"{username}@{host}"
            
        # Create SSH connection
        connection_id = self.ssh_manager.create_connection(
            host=host,
            port=port,
            username=username,
            password=password,
            key_path=key_path,
            name=name,
            auto_connect=False  # Don't connect yet, we'll do it in a thread
        )
        
        # Get the connection
        connection = self.ssh_manager.get_connection(connection_id)
        if not connection:
            logger.error(f"Failed to create SSH connection: {name}")
            return None
            
        # Create a background thread to establish the connection
        connect_thread = threading.Thread(
            target=self._connect_in_background,
            args=(connection_id, connection),
            daemon=True
        )
        
        # Store the connection thread
        self.connecting[connection_id] = connect_thread
        
        # Start the connection thread
        connect_thread.start()
        
        return connection_id
    
    def connect_from_profile(self, profile_id: str, password: Optional[str] = None) -> Optional[str]:
        """Connect using a saved profile"""
        connection_id = self.ssh_manager.connect_from_profile(profile_id, password)
        if connection_id:
            # Get the connection
            connection = self.ssh_manager.get_connection(connection_id)
            if connection:
                # Create a background thread to establish the connection
                connect_thread = threading.Thread(
                    target=self._connect_in_background,
                    args=(connection_id, connection),
                    daemon=True
                )
                
                # Store the connection thread
                self.connecting[connection_id] = connect_thread
                
                # Start the connection thread
                connect_thread.start()
                
        return connection_id
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """List all active SSH connections"""
        connections = []
        
        for connection in self.ssh_manager.get_all_connections():
            connections.append(connection.to_dict())
            
        return connections
    
    def list_profiles(self) -> Dict[str, Dict[str, Any]]:
        """List all saved SSH profiles"""
        return self.ssh_manager.get_all_profiles()
    
    def save_profile(self, name: str, host: str, port: int = 22, 
                    username: str = "", key_path: Optional[str] = None) -> str:
        """Save an SSH profile"""
        return self.ssh_manager.save_profile(name, host, port, username, key_path)
    
    def delete_profile(self, profile_id: str) -> bool:
        """Delete an SSH profile"""
        return self.ssh_manager.delete_profile(profile_id)
    
    def disconnect(self, connection_id: str) -> bool:
        """
        Disconnect from an SSH server.
        Returns True if successful, False otherwise.
        """
        # Check if there's a terminal session for this connection
        if connection_id in self.active_terminals:
            # Get the terminal
            _, terminal, terminal_thread = self.active_terminals[connection_id]
            
            # Set the terminal status
            terminal.set_connected(False)
            terminal.add_output("\n\nDisconnected from SSH server.\n")
            
            # The terminal thread will handle cleanup
            
        # Close the connection
        return self.ssh_manager.close_connection(connection_id)
    
    def stop(self):
        """Stop the SSH client and close all connections"""
        # Close all SSH connections
        self.ssh_manager.stop()
        
        # Wait for terminal threads to finish
        for connection_id, (_, _, terminal_thread) in list(self.active_terminals.items()):
            if terminal_thread.is_alive():
                # Give it a moment to clean up
                terminal_thread.join(timeout=1.0)
                
        # Clear state
        self.active_terminals = {}
        self.connecting = {}
        
        logger.info("SSH client stopped")
    
    def resize_terminal(self, connection_id: str, width: int, height: int) -> bool:
        """
        Resize an SSH terminal.
        Returns True if successful, False otherwise.
        """
        # Check if there's an active connection
        if connection_id not in self.active_terminals:
            logger.warning(f"No active terminal for connection: {connection_id}")
            return False
            
        # Get the connection
        connection, _, _ = self.active_terminals[connection_id]
        
        # Resize the terminal
        return connection.resize_terminal(width, height)
    
    def _connect_in_background(self, connection_id: str, connection: SSHConnection):
        """
        Background thread that establishes an SSH connection and launches a terminal.
        """
        try:
            # Attempt to connect
            success = connection.connect()
            
            # Remove from connecting list
            if connection_id in self.connecting:
                del self.connecting[connection_id]
                
            if not success:
                # Show notification for failure
                Notification.error(
                    title="SSH Connection Failed",
                    message=f"Could not connect to {connection.name}: {connection.error_message}"
                )
                return
                
            # Create terminal widget
            terminal = TerminalWidget(
                name=connection.name,
                on_input=lambda cmd: self._handle_terminal_input(connection_id, cmd),
                on_exit=lambda: self._handle_terminal_exit(connection_id)
            )
            
            # Register data callback
            connection.add_data_callback(terminal.add_output)
            
            # Update terminal status
            terminal.set_connected(True)
            terminal.add_output(f"Connected to {connection.host} as {connection.username}\n")
            
            # Create thread to run the terminal UI
            terminal_thread = threading.Thread(
                target=terminal.run,
                daemon=True
            )
            
            # Store the terminal and thread
            self.active_terminals[connection_id] = (connection, terminal, terminal_thread)
            
            # Start the terminal UI
            terminal_thread.start()
            
            # Show notification for successful connection
            Notification.success(
                title="SSH Connection Established",
                message=f"Connected to {connection.name}"
            )
            
        except Exception as e:
            logger.error(f"Error in SSH connect thread: {e}")
            
            # Show notification for error
            Notification.error(
                title="SSH Connection Error",
                message=f"Error connecting to {connection.name}: {str(e)}"
            )
    
    def _handle_terminal_input(self, connection_id: str, command: str):
        """Handle input from the terminal"""
        # Check if there's an active connection
        if connection_id not in self.active_terminals:
            logger.warning(f"No active connection for terminal input: {connection_id}")
            return
            
        # Get the connection
        connection, terminal, _ = self.active_terminals[connection_id]
        
        # Send the command with a newline
        if not command.endswith('\n'):
            command += '\n'
            
        connection.send_command(command)
    
    def _handle_terminal_exit(self, connection_id: str):
        """Handle terminal exit event"""
        # Check if there's an active connection
        if connection_id not in self.active_terminals:
            logger.warning(f"No active connection for terminal exit: {connection_id}")
            return
            
        # Get the connection
        connection, terminal, terminal_thread = self.active_terminals[connection_id]
        
        # Disconnect from SSH server
        connection.disconnect()
        
        # Clean up
        if connection_id in self.active_terminals:
            del self.active_terminals[connection_id]
            
        logger.info(f"Terminal closed for {connection.name}")
        
        # Show notification
        Notification.info(
            title="SSH Connection Closed",
            message=f"Disconnected from {connection.name}"
        ) 