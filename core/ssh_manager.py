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
    
    # SFTP functionality
    def open_sftp(self) -> Optional[paramiko.SFTPClient]:
        """
        Open an SFTP session for file transfers.
        Returns the SFTP client if successful, None otherwise.
        """
        if self.status != SSHConnectionStatus.CONNECTED or not self.transport:
            logger.warning(f"Cannot open SFTP: not connected to {self.name}")
            return None
            
        try:
            sftp = paramiko.SFTPClient.from_transport(self.transport)
            logger.info(f"Opened SFTP session for {self.name}")
            return sftp
        except Exception as e:
            logger.error(f"Error opening SFTP session: {e}")
            return None
            
    def upload_file(self, local_path: str, remote_path: str, 
                   callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Upload a file to the remote server using SFTP.
        
        Args:
            local_path: Path to the local file
            remote_path: Path where to store the file on the remote server
            callback: Optional callback function for progress updates (bytes_transferred, total_bytes)
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(local_path):
            logger.error(f"Local file not found: {local_path}")
            return False
            
        sftp = self.open_sftp()
        if not sftp:
            return False
            
        try:
            # Get file size for progress reporting
            file_size = os.path.getsize(local_path)
            
            # Prepare callback wrapper if a callback was provided
            cb_func = None
            if callback:
                def callback_wrapper(bytes_transferred, total_bytes):
                    callback(bytes_transferred, file_size)
                cb_func = callback_wrapper
            
            # Upload the file
            sftp.put(local_path, remote_path, callback=cb_func)
            logger.info(f"Uploaded {local_path} to {remote_path} on {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False
            
        finally:
            sftp.close()
            
    def download_file(self, remote_path: str, local_path: str,
                     callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Download a file from the remote server using SFTP.
        
        Args:
            remote_path: Path to the file on the remote server
            local_path: Path where to store the downloaded file
            callback: Optional callback function for progress updates (bytes_transferred, total_bytes)
            
        Returns:
            True if successful, False otherwise
        """
        sftp = self.open_sftp()
        if not sftp:
            return False
            
        try:
            # Get file stats for progress reporting
            file_stats = sftp.stat(remote_path)
            file_size = file_stats.st_size
            
            # Prepare callback wrapper if a callback was provided
            cb_func = None
            if callback:
                def callback_wrapper(bytes_transferred, total_bytes):
                    callback(bytes_transferred, file_size)
                cb_func = callback_wrapper
            
            # Download the file
            sftp.get(remote_path, local_path, callback=cb_func)
            logger.info(f"Downloaded {remote_path} from {self.name} to {local_path}")
            return True
            
        except FileNotFoundError:
            logger.error(f"Remote file not found: {remote_path}")
            return False
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
            
        finally:
            sftp.close()
            
    def list_directory(self, remote_path: str = '.') -> Optional[List[Dict[str, Any]]]:
        """
        List the contents of a directory on the remote server.
        
        Args:
            remote_path: Path to the directory on the remote server
            
        Returns:
            List of file/directory attributes or None if failed
        """
        sftp = self.open_sftp()
        if not sftp:
            return None
            
        try:
            # Get directory listing
            dir_items = sftp.listdir_attr(remote_path)
            
            # Convert to list of dictionaries
            result = []
            for item in dir_items:
                item_dict = {
                    "filename": item.filename,
                    "size": item.st_size,
                    "mtime": item.st_mtime,  # Modification time
                    "mode": item.st_mode,    # File permissions
                    "is_directory": bool(item.st_mode & 0o40000),  # Check if it's a directory
                    "is_file": bool(item.st_mode & 0o100000)       # Check if it's a regular file
                }
                result.append(item_dict)
                
            return result
                
        except Exception as e:
            logger.error(f"Error listing directory {remote_path}: {e}")
            return None
            
        finally:
            sftp.close()
    
    # SSH Tunneling functionality
    def create_tunnel(self, local_port: int, remote_host: str, remote_port: int) -> bool:
        """
        Create an SSH tunnel from local_port to remote_host:remote_port.
        This implements local port forwarding: connections to local_port
        will be forwarded to remote_host:remote_port through the SSH connection.
        
        Args:
            local_port: Local port to listen on
            remote_host: Remote host to connect to
            remote_port: Remote port to connect to
            
        Returns:
            True if successful, False otherwise
        """
        if self.status != SSHConnectionStatus.CONNECTED or not self.transport:
            logger.warning(f"Cannot create tunnel: not connected to {self.name}")
            return False
            
        try:
            # Check if port is available
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', local_port))
            sock.close()
            
            if result == 0:
                logger.error(f"Local port {local_port} is already in use")
                return False
                
            # Start port forwarding
            self.transport.request_port_forward('127.0.0.1', local_port, remote_host, remote_port)
            logger.info(f"Created tunnel: localhost:{local_port} -> {remote_host}:{remote_port} via {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating tunnel: {e}")
            return False
            
    def remove_tunnel(self, local_port: int) -> bool:
        """
        Remove an SSH tunnel.
        
        Args:
            local_port: Local port the tunnel is listening on
            
        Returns:
            True if successful, False otherwise
        """
        if self.status != SSHConnectionStatus.CONNECTED or not self.transport:
            logger.warning(f"Cannot remove tunnel: not connected to {self.name}")
            return False
            
        try:
            self.transport.cancel_port_forward('127.0.0.1', local_port)
            logger.info(f"Removed tunnel on localhost:{local_port}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing tunnel: {e}")
            return False
            
    def create_reverse_tunnel(self, server_port: int, local_host: str, local_port: int) -> bool:
        """
        Create a reverse SSH tunnel from server_port to local_host:local_port.
        This implements remote port forwarding: connections to server_port on the remote
        server will be forwarded to local_host:local_port on the local machine.
        
        Args:
            server_port: Port on the remote server to listen on
            local_host: Local host to connect to
            local_port: Local port to connect to
            
        Returns:
            True if successful, False otherwise
        """
        if self.status != SSHConnectionStatus.CONNECTED or not self.transport:
            logger.warning(f"Cannot create reverse tunnel: not connected to {self.name}")
            return False
            
        try:
            # Start reverse port forwarding
            self.transport.request_port_forward('', server_port, local_host, local_port)
            logger.info(f"Created reverse tunnel: {self.host}:{server_port} -> {local_host}:{local_port}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating reverse tunnel: {e}")
            return False
            
    def remove_reverse_tunnel(self, server_port: int) -> bool:
        """
        Remove a reverse SSH tunnel.
        
        Args:
            server_port: Port on the remote server the tunnel is listening on
            
        Returns:
            True if successful, False otherwise
        """
        if self.status != SSHConnectionStatus.CONNECTED or not self.transport:
            logger.warning(f"Cannot remove reverse tunnel: not connected to {self.name}")
            return False
            
        try:
            self.transport.cancel_port_forward('', server_port)
            logger.info(f"Removed reverse tunnel on {self.host}:{server_port}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing reverse tunnel: {e}")
            return False


class SSHManager:
    """
    Manages multiple SSH connections and configuration profiles.
    """
    
    # Location for storing SSH profiles
    CONFIG_DIRECTORY = os.path.expanduser("~/.ztalk/ssh")
    PROFILES_FILE = os.path.join(CONFIG_DIRECTORY, "profiles.json")
    KEYS_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "keys")
    WORKFLOWS_DIRECTORY = os.path.join(CONFIG_DIRECTORY, "workflows")
    
    def __init__(self):
        self.connections: Dict[str, SSHConnection] = {}
        self.profiles: Dict[str, Dict[str, Any]] = {}
        self.workflows: Dict[str, Dict[str, Any]] = {}
        
        # Ensure config directories exist
        os.makedirs(self.CONFIG_DIRECTORY, exist_ok=True)
        os.makedirs(self.KEYS_DIRECTORY, exist_ok=True)
        os.makedirs(self.WORKFLOWS_DIRECTORY, exist_ok=True)
        
        # Load saved profiles and workflows
        self._load_profiles()
        self._load_workflows()
        
        # Status check thread
        self.running = True
        self.check_thread = threading.Thread(target=self._check_connections, daemon=True)
        self.check_thread.start()
        
        # Active tunnels tracking
        self.active_tunnels: Dict[str, List[Dict[str, Any]]] = {}  # {connection_id: [{local_port, remote_host, remote_port}]}
        
        # Key management
        self.private_keys: Dict[str, paramiko.PKey] = {}  # Cache of loaded private keys
    
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
    
    # Key management methods
    def generate_key_pair(self, key_name: str, key_type: str = "rsa", 
                         bits: int = 2048, passphrase: Optional[str] = None) -> Optional[str]:
        """
        Generate a new SSH key pair.
        
        Args:
            key_name: Name for the key (will be used as filename)
            key_type: Type of key (rsa, dsa, ecdsa, ed25519)
            bits: Key size in bits (for RSA and DSA)
            passphrase: Optional passphrase to encrypt the private key
            
        Returns:
            Path to the private key if successful, None otherwise
        """
        key_path = os.path.join(self.KEYS_DIRECTORY, f"{key_name}")
        public_key_path = f"{key_path}.pub"
        
        # Check if key already exists
        if os.path.exists(key_path):
            logger.warning(f"Key {key_name} already exists")
            return None
            
        try:
            # Generate key based on type
            if key_type.lower() == "rsa":
                key = paramiko.RSAKey.generate(bits)
            elif key_type.lower() == "dsa":
                key = paramiko.DSSKey.generate(bits)
            elif key_type.lower() == "ecdsa":
                key = paramiko.ECDSAKey.generate()
            elif key_type.lower() == "ed25519":
                key = paramiko.Ed25519Key.generate()
            else:
                logger.error(f"Unsupported key type: {key_type}")
                return None
                
            # Save private key
            key.write_private_key_file(key_path, password=passphrase)
            
            # Save public key
            with open(public_key_path, 'w') as f:
                f.write(f"{key.get_name()} {key.get_base64()} {key_name}\n")
                
            logger.info(f"Generated {key_type} key pair: {key_name}")
            return key_path
            
        except Exception as e:
            logger.error(f"Error generating key pair: {e}")
            return None
            
    def import_key(self, key_path: str, new_name: Optional[str] = None, 
                  passphrase: Optional[str] = None) -> Optional[str]:
        """
        Import an existing SSH key.
        
        Args:
            key_path: Path to the private key file
            new_name: New name for the key (default: use filename)
            passphrase: Passphrase for the key if encrypted
            
        Returns:
            Path to the imported key if successful, None otherwise
        """
        if not os.path.exists(key_path):
            logger.error(f"Key file not found: {key_path}")
            return None
            
        try:
            # Determine key name
            if not new_name:
                new_name = os.path.basename(key_path)
                
            # Destination path
            dest_path = os.path.join(self.KEYS_DIRECTORY, new_name)
            
            # Check if already exists
            if os.path.exists(dest_path):
                logger.warning(f"Key {new_name} already exists in keys directory")
                return None
                
            # Try to load the key to verify it's valid
            try:
                key = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
            except paramiko.ssh_exception.SSHException:
                try:
                    key = paramiko.DSSKey.from_private_key_file(key_path, password=passphrase)
                except paramiko.ssh_exception.SSHException:
                    try:
                        key = paramiko.ECDSAKey.from_private_key_file(key_path, password=passphrase)
                    except paramiko.ssh_exception.SSHException:
                        key = paramiko.Ed25519Key.from_private_key_file(key_path, password=passphrase)
                        
            # Copy the key file
            import shutil
            shutil.copy2(key_path, dest_path)
            
            # Generate public key if it doesn't exist
            public_key_path = f"{dest_path}.pub"
            if not os.path.exists(public_key_path):
                with open(public_key_path, 'w') as f:
                    f.write(f"{key.get_name()} {key.get_base64()} {new_name}\n")
                    
            logger.info(f"Imported SSH key: {new_name}")
            return dest_path
            
        except Exception as e:
            logger.error(f"Error importing key: {e}")
            return None
            
    def export_public_key(self, key_name: str) -> Optional[str]:
        """
        Get the public key text for a given private key.
        
        Args:
            key_name: Name of the key
            
        Returns:
            Public key content if successful, None otherwise
        """
        public_key_path = os.path.join(self.KEYS_DIRECTORY, f"{key_name}.pub")
        
        if not os.path.exists(public_key_path):
            logger.error(f"Public key not found: {key_name}.pub")
            return None
            
        try:
            with open(public_key_path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error reading public key: {e}")
            return None
            
    def delete_key(self, key_name: str) -> bool:
        """
        Delete an SSH key pair.
        
        Args:
            key_name: Name of the key
            
        Returns:
            True if successful, False otherwise
        """
        private_key_path = os.path.join(self.KEYS_DIRECTORY, key_name)
        public_key_path = f"{private_key_path}.pub"
        
        try:
            # Delete private key
            if os.path.exists(private_key_path):
                os.remove(private_key_path)
                
            # Delete public key
            if os.path.exists(public_key_path):
                os.remove(public_key_path)
                
            logger.info(f"Deleted SSH key: {key_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting key: {e}")
            return False
            
    def list_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        List all SSH keys in the keys directory.
        
        Returns:
            Dictionary of key names and attributes
        """
        keys = {}
        
        try:
            for filename in os.listdir(self.KEYS_DIRECTORY):
                # Only look at private keys (not .pub files)
                if filename.endswith('.pub'):
                    continue
                    
                key_path = os.path.join(self.KEYS_DIRECTORY, filename)
                if os.path.isfile(key_path):
                    # Get key details
                    key_type = "unknown"
                    public_key_path = f"{key_path}.pub"
                    
                    # Try to determine key type from public key
                    if os.path.exists(public_key_path):
                        try:
                            with open(public_key_path, 'r') as f:
                                content = f.read().strip()
                                if content.startswith('ssh-rsa'):
                                    key_type = "rsa"
                                elif content.startswith('ssh-dss'):
                                    key_type = "dsa"
                                elif content.startswith('ecdsa-sha2'):
                                    key_type = "ecdsa"
                                elif content.startswith('ssh-ed25519'):
                                    key_type = "ed25519"
                        except Exception:
                            pass
                            
                    keys[filename] = {
                        "name": filename,
                        "path": key_path,
                        "type": key_type,
                        "has_public_key": os.path.exists(public_key_path)
                    }
                    
            return keys
            
        except Exception as e:
            logger.error(f"Error listing keys: {e}")
            return {}
            
    # SSH Workflow Automation
    def create_workflow(self, name: str, description: str, 
                       target_profiles: List[str], commands: List[str]) -> str:
        """
        Create an automated SSH workflow.
        
        Args:
            name: Name for the workflow
            description: Description of what the workflow does
            target_profiles: List of SSH profile IDs to target
            commands: List of commands to execute
            
        Returns:
            Workflow ID
        """
        workflow_id = name.lower().replace(" ", "_")
        
        # Generate a unique ID if the name is already taken
        if workflow_id in self.workflows:
            workflow_id = f"{workflow_id}_{int(time.time())}"
            
        self.workflows[workflow_id] = {
            "name": name,
            "description": description,
            "target_profiles": target_profiles,
            "commands": commands,
            "created": time.time()
        }
        
        self._save_workflows()
        logger.info(f"Created SSH workflow: {name} ({workflow_id})")
        return workflow_id
        
    def delete_workflow(self, workflow_id: str) -> bool:
        """
        Delete an SSH workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            True if successful, False otherwise
        """
        if workflow_id in self.workflows:
            del self.workflows[workflow_id]
            self._save_workflows()
            logger.info(f"Deleted SSH workflow: {workflow_id}")
            return True
        else:
            logger.warning(f"Workflow not found: {workflow_id}")
            return False
            
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific workflow by ID"""
        return self.workflows.get(workflow_id)
        
    def get_all_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get all SSH workflows"""
        return self.workflows.copy()
        
    def execute_workflow(self, workflow_id: str, 
                        passwords: Optional[Dict[str, str]] = None,
                        callback: Optional[Callable[[str, str, str], None]] = None) -> Dict[str, Any]:
        """
        Execute an SSH workflow on target servers.
        
        Args:
            workflow_id: ID of the workflow to execute
            passwords: Dictionary of profile IDs and passwords (for profiles without key authentication)
            callback: Optional callback function (profile_id, command, output)
            
        Returns:
            Dictionary with execution results
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            logger.warning(f"Workflow not found: {workflow_id}")
            return {"success": False, "error": "Workflow not found"}
            
        # Results dictionary
        results = {
            "workflow_id": workflow_id,
            "name": workflow["name"],
            "start_time": time.time(),
            "end_time": None,
            "success": True,
            "results": {}
        }
        
        # Execute on each target profile
        for profile_id in workflow["target_profiles"]:
            profile = self.profiles.get(profile_id)
            if not profile:
                logger.warning(f"Profile not found: {profile_id}")
                results["results"][profile_id] = {
                    "success": False,
                    "error": "Profile not found",
                    "commands": []
                }
                continue
                
            # Get password if provided
            password = None
            if passwords and profile_id in passwords:
                password = passwords[profile_id]
                
            # Create connection
            connection_id = self.connect_from_profile(profile_id, password)
            if not connection_id:
                results["results"][profile_id] = {
                    "success": False,
                    "error": "Failed to connect",
                    "commands": []
                }
                continue
                
            connection = self.connections[connection_id]
            
            # Execute commands
            profile_results = {
                "success": True,
                "commands": []
            }
            
            for cmd in workflow["commands"]:
                cmd_result = {
                    "command": cmd,
                    "success": False,
                    "output": ""
                }
                
                try:
                    # Execute command
                    stdin, stdout, stderr = connection.client.exec_command(cmd, timeout=30)
                    stdin.close()
                    
                    # Get command output
                    output = stdout.read().decode('utf-8', errors='replace')
                    error = stderr.read().decode('utf-8', errors='replace')
                    
                    if error:
                        output += f"\nERROR: {error}"
                        
                    cmd_result["success"] = stdout.channel.recv_exit_status() == 0
                    cmd_result["output"] = output
                    
                    # Call callback if provided
                    if callback:
                        callback(profile_id, cmd, output)
                        
                except Exception as e:
                    cmd_result["output"] = f"Error: {str(e)}"
                    
                profile_results["commands"].append(cmd_result)
                
                # If a command fails and it's critical, stop execution for this profile
                if not cmd_result["success"] and cmd.strip().startswith("!"):
                    profile_results["success"] = False
                    profile_results["error"] = f"Critical command failed: {cmd}"
                    break
                    
            # Close connection
            self.close_connection(connection_id)
            
            # Store results for this profile
            results["results"][profile_id] = profile_results
            
        # Update end time
        results["end_time"] = time.time()
        
        # Check if any profile failed
        for profile_id, profile_result in results["results"].items():
            if not profile_result.get("success", False):
                results["success"] = False
                break
                
        return results
        
    def _load_workflows(self):
        """Load SSH workflows from file"""
        workflows_file = os.path.join(self.WORKFLOWS_DIRECTORY, "workflows.json")
        if os.path.exists(workflows_file):
            try:
                import json
                with open(workflows_file, 'r') as f:
                    self.workflows = json.load(f)
                logger.info(f"Loaded {len(self.workflows)} SSH workflows")
            except Exception as e:
                logger.error(f"Error loading SSH workflows: {e}")
                self.workflows = {}
                
    def _save_workflows(self):
        """Save SSH workflows to file"""
        try:
            import json
            workflows_file = os.path.join(self.WORKFLOWS_DIRECTORY, "workflows.json")
            with open(workflows_file, 'w') as f:
                json.dump(self.workflows, f, indent=2)
            logger.info(f"Saved {len(self.workflows)} SSH workflows")
        except Exception as e:
            logger.error(f"Error saving SSH workflows: {e}") 