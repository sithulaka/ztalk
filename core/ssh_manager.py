"""
SSH Connection Manager for ZTalk

Handles SSH connection creation, management, and interaction.
Provides an interface to create, monitor, and communicate with multiple SSH sessions.
"""

import os
import threading
import time
import logging
import uuid
import socket
import paramiko
from typing import Dict, List, Set, Optional, Callable, Any, Tuple
from enum import Enum, auto
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class SSHConnectionStatus(Enum):
    """Status of an SSH connection"""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    FAILED = auto()
    CLOSED = auto()


class SSHConnection:
    """Represents a single SSH connection"""
    
    def __init__(self,
                connection_id: str,
                host: str,
                port: int = 22,
                username: str = "",
                password: Optional[str] = None,
                key_path: Optional[str] = None,
                name: Optional[str] = None):
        
        self.connection_id = connection_id
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.name = name or f"{username}@{host}"
        
        # Connection state
        self.status = SSHConnectionStatus.DISCONNECTED
        self.error_message: Optional[str] = None
        self.connected_time: Optional[float] = None
        self.last_activity: float = time.time()
        
        # SSH components
        self.client: Optional[paramiko.SSHClient] = None
        self.transport: Optional[paramiko.Transport] = None
        self.channel: Optional[paramiko.Channel] = None
        
        # Data callbacks
        self.data_callbacks: List[Callable[[str], None]] = []
        
        # Session information
        self.terminal_type = "xterm-256color"
        self.term_width = 80
        self.term_height = 24
        
        # Buffer for received data
        self.data_buffer = ""
        self.data_lock = threading.Lock()
        
        # Reader thread
        self.reader_thread: Optional[threading.Thread] = None
        self.running = False
        
    def connect(self) -> bool:
        """
        Establish an SSH connection.
        Returns True if successful, False otherwise.
        """
        if self.status == SSHConnectionStatus.CONNECTED:
            return True
            
        self.status = SSHConnectionStatus.CONNECTING
        self.error_message = None
        
        try:
            # Create SSH client
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "timeout": 10
            }
            
            # Add authentication method
            if self.password:
                connect_kwargs["password"] = self.password
            elif self.key_path:
                key_path = os.path.expanduser(self.key_path)
                if os.path.exists(key_path):
                    connect_kwargs["key_filename"] = key_path
                else:
                    self.error_message = f"Key file not found: {self.key_path}"
                    self.status = SSHConnectionStatus.FAILED
                    return False
            
            # Connect to the SSH server
            self.client.connect(**connect_kwargs)
            
            # Open a channel
            self.transport = self.client.get_transport()
            if not self.transport:
                self.error_message = "Failed to get transport"
                self.status = SSHConnectionStatus.FAILED
                return False
                
            self.channel = self.transport.open_session()
            self.channel.get_pty(
                term=self.terminal_type,
                width=self.term_width,
                height=self.term_height
            )
            self.channel.invoke_shell()
            
            # Update status
            self.status = SSHConnectionStatus.CONNECTED
            self.connected_time = time.time()
            self.last_activity = time.time()
            
            # Start reader thread
            self.running = True
            self.reader_thread = threading.Thread(target=self._read_output, daemon=True)
            self.reader_thread.start()
            
            logger.info(f"Connected to SSH server: {self.name}")
            return True
            
        except socket.gaierror:
            self.error_message = f"Could not resolve hostname: {self.host}"
            self.status = SSHConnectionStatus.FAILED
            logger.error(f"SSH connection failed: {self.error_message}")
            return False
            
        except paramiko.AuthenticationException:
            self.error_message = "Authentication failed"
            self.status = SSHConnectionStatus.FAILED
            logger.error(f"SSH connection failed: {self.error_message}")
            return False
            
        except paramiko.SSHException as e:
            self.error_message = f"SSH error: {str(e)}"
            self.status = SSHConnectionStatus.FAILED
            logger.error(f"SSH connection failed: {self.error_message}")
            return False
            
        except Exception as e:
            self.error_message = f"Connection error: {str(e)}"
            self.status = SSHConnectionStatus.FAILED
            logger.error(f"SSH connection failed: {self.error_message}")
            return False
    
    def disconnect(self):
        """Close the SSH connection"""
        self.running = False
        
        # Close channel
        if self.channel:
            try:
                if not self.channel.closed:
                    self.channel.close()
            except Exception as e:
                logger.error(f"Error closing channel: {e}")
            finally:
                self.channel = None
        
        # Close client
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.error(f"Error closing SSH client: {e}")
            finally:
                self.client = None
                
        self.status = SSHConnectionStatus.CLOSED
        logger.info(f"Disconnected from SSH server: {self.name}")
    
    def send_command(self, command: str) -> bool:
        """
        Send a command to the SSH session.
        Returns True if successful, False otherwise.
        """
        if self.status != SSHConnectionStatus.CONNECTED or not self.channel:
            logger.warning(f"Cannot send command: not connected to {self.name}")
            return False
            
        try:
            self.channel.send(command)
            self.last_activity = time.time()
            return True
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
    
    def resize_terminal(self, width: int, height: int) -> bool:
        """
        Resize the terminal.
        Returns True if successful, False otherwise.
        """
        if self.status != SSHConnectionStatus.CONNECTED or not self.channel:
            logger.warning(f"Cannot resize terminal: not connected to {self.name}")
            return False
            
        try:
            self.term_width = width
            self.term_height = height
            self.channel.resize_pty(width=width, height=height)
            return True
        except Exception as e:
            logger.error(f"Error resizing terminal: {e}")
            return False
    
    def add_data_callback(self, callback: Callable[[str], None]):
        """Register a callback function to receive data"""
        self.data_callbacks.append(callback)
        
    def remove_data_callback(self, callback: Callable[[str], None]):
        """Remove a data callback"""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    def _read_output(self):
        """
        Background thread that reads output from the SSH channel
        and notifies callbacks
        """
        logger.debug(f"Started SSH reader thread for {self.name}")
        
        while self.running and self.channel and not self.channel.closed:
            try:
                # Check if channel is still active
                if self.channel.recv_ready():
                    data = self.channel.recv(1024).decode('utf-8', errors='replace')
                    self.last_activity = time.time()
                    
                    # Append to buffer
                    with self.data_lock:
                        self.data_buffer += data
                    
                    # Notify callbacks
                    for callback in self.data_callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            logger.error(f"Error in SSH data callback: {e}")
                
                # Check if channel is closed
                if self.channel.exit_status_ready():
                    logger.debug(f"SSH channel exited for {self.name}")
                    break
                    
                # Avoid tight polling
                time.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Error reading from SSH channel: {e}")
                break
        
        # Mark as disconnected if we're exiting due to closed channel
        if self.running:
            self.status = SSHConnectionStatus.DISCONNECTED
            logger.info(f"SSH connection closed: {self.name}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for serialization"""
        return {
            "connection_id": self.connection_id,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "key_path": self.key_path,
            "name": self.name,
            "status": self.status.name,
            "connected_time": self.connected_time,
            "last_activity": self.last_activity
        }


class SSHManager:
    """
    Manages multiple SSH connections and configuration profiles.
    """
    
    # Location for storing SSH profiles
    CONFIG_DIRECTORY = os.path.expanduser("~/.ztalk/ssh")
    PROFILES_FILE = os.path.join(CONFIG_DIRECTORY, "profiles.json")
    
    def __init__(self):
        self.connections: Dict[str, SSHConnection] = {}
        self.profiles: Dict[str, Dict[str, Any]] = {}
        
        # Ensure config directory exists
        os.makedirs(self.CONFIG_DIRECTORY, exist_ok=True)
        
        # Load saved profiles
        self._load_profiles()
        
        # Status check thread
        self.running = True
        self.check_thread = threading.Thread(target=self._check_connections, daemon=True)
        self.check_thread.start()
    
    def start(self) -> bool:
        """Start the SSH manager"""
        # Nothing special to do here as we've already initialized everything
        return True
    
    def stop(self):
        """Stop the SSH manager and close all connections"""
        self.running = False
        
        # Close all connections
        for conn_id, connection in list(self.connections.items()):
            connection.disconnect()
            
        # Save profiles
        self._save_profiles()
        
        logger.info("SSH manager stopped")
    
    def create_connection(self, 
                         host: str, 
                         port: int = 22, 
                         username: str = "", 
                         password: Optional[str] = None,
                         key_path: Optional[str] = None,
                         name: Optional[str] = None,
                         auto_connect: bool = True) -> str:
        """
        Create a new SSH connection.
        Returns the connection ID.
        """
        connection_id = str(uuid.uuid4())
        connection = SSHConnection(
            connection_id=connection_id,
            host=host,
            port=port,
            username=username,
            password=password,
            key_path=key_path,
            name=name
        )
        
        self.connections[connection_id] = connection
        
        # Connect if requested
        if auto_connect:
            connection.connect()
            
        logger.info(f"Created SSH connection: {connection.name} ({connection_id})")
        return connection_id
    
    def get_connection(self, connection_id: str) -> Optional[SSHConnection]:
        """Get a specific SSH connection by ID"""
        return self.connections.get(connection_id)
    
    def get_all_connections(self) -> List[SSHConnection]:
        """Get all SSH connections"""
        return list(self.connections.values())
    
    def close_connection(self, connection_id: str) -> bool:
        """
        Close an SSH connection.
        Returns True if successful, False otherwise.
        """
        connection = self.connections.get(connection_id)
        if not connection:
            logger.warning(f"Connection not found: {connection_id}")
            return False
            
        connection.disconnect()
        del self.connections[connection_id]
        logger.info(f"Closed SSH connection: {connection.name} ({connection_id})")
        return True
    
    def save_profile(self, name: str, host: str, port: int = 22, 
                    username: str = "", key_path: Optional[str] = None) -> str:
        """
        Save an SSH connection profile.
        Returns the profile ID.
        """
        profile_id = name.lower().replace(" ", "_")
        
        # Generate a unique ID if the name is already taken
        if profile_id in self.profiles:
            profile_id = f"{profile_id}_{int(time.time())}"
            
        self.profiles[profile_id] = {
            "name": name,
            "host": host,
            "port": port,
            "username": username,
            "key_path": key_path,
        }
        
        self._save_profiles()
        logger.info(f"Saved SSH profile: {name} ({profile_id})")
        return profile_id
    
    def delete_profile(self, profile_id: str) -> bool:
        """
        Delete an SSH profile.
        Returns True if successful, False otherwise.
        """
        if profile_id in self.profiles:
            del self.profiles[profile_id]
            self._save_profiles()
            logger.info(f"Deleted SSH profile: {profile_id}")
            return True
        else:
            logger.warning(f"Profile not found: {profile_id}")
            return False
    
    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific profile by ID"""
        return self.profiles.get(profile_id)
    
    def get_all_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all SSH profiles"""
        return self.profiles.copy()
    
    def connect_from_profile(self, 
                           profile_id: str, 
                           password: Optional[str] = None) -> Optional[str]:
        """
        Create a connection from a profile.
        Returns the connection ID if successful, None otherwise.
        """
        profile = self.profiles.get(profile_id)
        if not profile:
            logger.warning(f"Profile not found: {profile_id}")
            return None
            
        connection_id = self.create_connection(
            host=profile["host"],
            port=profile["port"],
            username=profile["username"],
            password=password,
            key_path=profile.get("key_path"),
            name=profile["name"]
        )
        
        return connection_id
    
    def _load_profiles(self):
        """Load SSH profiles from file"""
        if os.path.exists(self.PROFILES_FILE):
            try:
                import json
                with open(self.PROFILES_FILE, 'r') as f:
                    self.profiles = json.load(f)
                logger.info(f"Loaded {len(self.profiles)} SSH profiles")
            except Exception as e:
                logger.error(f"Error loading SSH profiles: {e}")
                self.profiles = {}
    
    def _save_profiles(self):
        """Save SSH profiles to file"""
        try:
            import json
            with open(self.PROFILES_FILE, 'w') as f:
                json.dump(self.profiles, f, indent=2)
            logger.info(f"Saved {len(self.profiles)} SSH profiles")
        except Exception as e:
            logger.error(f"Error saving SSH profiles: {e}")
    
    def _check_connections(self):
        """
        Background thread that periodically checks connections
        to see if they're still alive
        """
        check_interval = 30  # seconds
        
        while self.running:
            try:
                current_time = time.time()
                
                for conn_id, connection in list(self.connections.items()):
                    # Check for inactive connections (15 minutes with no activity)
                    if (connection.status == SSHConnectionStatus.CONNECTED and 
                        (current_time - connection.last_activity) > 15 * 60):
                        logger.info(f"Closing inactive SSH connection: {connection.name}")
                        connection.disconnect()
                        
                    # Attempt to reconnect failed connections that are less than 5 minutes old
                    elif (connection.status == SSHConnectionStatus.FAILED and 
                          connection.error_message and
                          "Connection refused" in connection.error_message and
                          (current_time - connection.last_activity) < 5 * 60):
                        logger.info(f"Attempting to reconnect: {connection.name}")
                        connection.connect()
                        
            except Exception as e:
                logger.error(f"Error checking SSH connections: {e}")
                
            # Sleep for the check interval
            time.sleep(check_interval) 