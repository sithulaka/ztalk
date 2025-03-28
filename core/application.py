"""
ZTalk Application Core

The central application coordinator that integrates all core components:
- Network management
- Peer discovery
- Messaging
- SSH connections
"""

import logging
import threading
import time
import os
import json
from typing import Dict, List, Set, Optional, Callable, Any, Tuple

from core.network_manager import NetworkManager
from core.peer_discovery import PeerDiscovery, ZTalkPeer
from core.messaging import MessageHandler, Message, MessageType
from core.ssh_manager import SSHManager, SSHConnection, SSHConnectionStatus
from core.dhcp_server import DHCPServer  # Import DHCPServer

# Configure logging
logger = logging.getLogger(__name__)

class ZTalkApp:
    """
    The main ZTalk application class that coordinates all core components.
    """
    
    # Application constants
    DEFAULT_DISCOVERY_PORT = 8989
    DEFAULT_MESSAGING_PORT = 8990
    DEFAULT_SSH_PORT = 22
    CONFIG_DIRECTORY = os.path.expanduser("~/.ztalk")
    CONFIG_FILE = os.path.join(CONFIG_DIRECTORY, "config.json")
    
    def __init__(self):
        # Configuration
        self.config = self._load_config()
        
        # Core components
        self.network_manager = NetworkManager()
        self.peer_discovery = None  # Will be initialized after network manager starts
        self.message_handler = None  # Will be initialized after peer discovery starts
        self.ssh_manager = None     # Will be initialized after network manager starts
        self.dhcp_server = None     # Will be initialized if enabled in config
        
        # Status
        self.running = False
        self.startup_time = None
        
        # Event listeners
        self.peer_listeners: List[Callable[[str, ZTalkPeer], None]] = []
        self.message_listeners: List[Callable[[Message], None]] = []
        self.network_listeners: List[Callable[[Dict[str, str], Dict[str, str]], None]] = []
        self.ssh_listeners: List[Callable[[str, SSHConnection], None]] = []
        
        # User information
        self.username = self.config.get("username", os.environ.get("USER", "user"))
        
        # Groups
        self.groups: Dict[str, Dict[str, Any]] = self.config.get("groups", {})
        
        # DHCP settings - disabled by default
        self.dhcp_enabled = self.config.get("dhcp_enabled", False)
        self.dhcp_network = self.config.get("dhcp_network", "192.168.100.0/24")
        self.dhcp_server_ip = self.config.get("dhcp_server_ip", None)
        
    def start(self) -> bool:
        """
        Start the ZTalk application.
        Initializes and starts all core components.
        """
        if self.running:
            logger.warning("Application is already running")
            return True
            
        try:
            logger.info("Starting ZTalk application")
            self.startup_time = time.time()
            
            # Start network manager
            logger.info("Starting network manager")
            if not self.network_manager.start():
                logger.error("Failed to start network manager")
                return False
                
            # Start DHCP server if enabled
            if self.dhcp_enabled:
                logger.info("Starting DHCP server (enabled in config)")
                self._start_dhcp_server()
            else:
                logger.info("DHCP server disabled (configure in settings to enable)")
                
            # Initialize and start peer discovery
            logger.info("Starting peer discovery")
            discovery_port = self.config.get("discovery_port", self.DEFAULT_DISCOVERY_PORT)
            self.peer_discovery = PeerDiscovery(self.network_manager, port=discovery_port)
            self.peer_discovery.update_username(self.username)
            
            # Add our listener before starting
            self.peer_discovery.add_peer_listener(self._on_peer_event)
            
            if not self.peer_discovery.start():
                logger.error("Failed to start peer discovery")
                self.network_manager.stop()
                return False
                
            # Initialize and start message handler
            logger.info("Starting message handler")
            messaging_port = self.config.get("messaging_port", self.DEFAULT_MESSAGING_PORT)
            self.message_handler = MessageHandler(
                peer_id=self.peer_discovery.instance_id,
                username=self.username,
                port=messaging_port
            )
            
            # Add our listener before starting
            self.message_handler.add_message_handler(self._on_message_received)
            
            if not self.message_handler.start():
                logger.error("Failed to start message handler")
                self.peer_discovery.stop()
                self.network_manager.stop()
                return False
                
            # Initialize and start SSH manager
            logger.info("Starting SSH manager")
            self.ssh_manager = SSHManager()
            if not self.ssh_manager.start():
                logger.warning("Failed to start SSH manager, continuing without SSH support")
                
            # Register network interface listener
            self.network_manager.add_interface_change_listener(self._on_network_change)
            
            # We're now running
            self.running = True
            logger.info(f"ZTalk application started successfully with username: {self.username}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting application: {e}")
            self.stop()
            return False
            
    def stop(self) -> bool:
        """
        Stop the ZTalk application.
        Stops all core components in the correct order.
        """
        logger.info("Stopping ZTalk application")
        
        try:
            # Stop message handler first
            if self.message_handler:
                self.message_handler.stop()
                
            # Stop SSH manager
            if self.ssh_manager:
                self.ssh_manager.stop()
                
            # Stop DHCP server if running
            if self.dhcp_server:
                self.dhcp_server.stop()
                
            # Stop peer discovery
            if self.peer_discovery:
                self.peer_discovery.stop()
                
            # Stop network manager last
            if self.network_manager:
                self.network_manager.stop()
                
            # Save config
            self._save_config()
                
            self.running = False
            logger.info("ZTalk application stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping application: {e}")
            self.running = False
            return False
            
    def restart(self) -> bool:
        """Restart the application"""
        self.stop()
        time.sleep(1)  # Brief pause to ensure everything is stopped
        return self.start()
    
    def set_username(self, username: str) -> bool:
        """Update the username"""
        if not username or len(username) < 2:
            logger.warning("Invalid username")
            return False
            
        self.username = username
        self.config["username"] = username
        
        # Update components
        if self.peer_discovery:
            self.peer_discovery.update_username(username)
            
        if self.message_handler:
            self.message_handler.username = username
            
        self._save_config()
        logger.info(f"Username changed to: {username}")
        return True
    
    def get_peers(self) -> List[ZTalkPeer]:
        """Get all discovered peers"""
        if not self.peer_discovery:
            return []
        return self.peer_discovery.get_all_peers()
    
    def get_active_peers(self) -> List[ZTalkPeer]:
        """Get only active peers"""
        if not self.peer_discovery:
            return []
        return self.peer_discovery.get_active_peers()
    
    def send_message(self, 
                   content: str, 
                   peer_id: Optional[str] = None,
                   group_id: Optional[str] = None) -> Optional[str]:
        """
        Send a message to a peer or group.
        Returns the message ID if successful, None otherwise.
        """
        if not self.message_handler:
            logger.warning("Message handler not initialized")
            return None
            
        if not self.peer_discovery:
            logger.warning("Peer discovery not initialized")
            return None
            
        if not content or not (peer_id or group_id):
            logger.warning("Invalid message parameters")
            return None
            
        # Handle direct message to a peer
        if peer_id:
            peer = self.peer_discovery.get_peer(peer_id)
            if not peer:
                logger.warning(f"Unknown peer: {peer_id}")
                return None
                
            # Send the message
            return self.message_handler.send_direct_message(
                content=content,
                peer_id=peer_id,
                address=(peer.ip_address, self.DEFAULT_MESSAGING_PORT),
                metadata={"needs_ack": True}
            )
            
        # Handle group message
        elif group_id:
            if group_id not in self.groups:
                logger.warning(f"Unknown group: {group_id}")
                return None
                
            # Get addresses for all peers in the group
            addresses = []
            for peer in self.peer_discovery.get_active_peers():
                # Skip peers that aren't in this group
                if group_id in self.groups and "members" in self.groups[group_id]:
                    if peer.peer_id not in self.groups[group_id]["members"]:
                        continue
                addresses.append((peer.ip_address, self.DEFAULT_MESSAGING_PORT))
                
            if not addresses:
                logger.warning(f"No active peers in group: {group_id}")
                return None
                
            # Send the group message
            return self.message_handler.send_group_message(
                content=content,
                group_id=group_id,
                addresses=addresses,
                metadata={"needs_ack": True}
            )
            
        return None
    
    def broadcast_message(self, content: str) -> Optional[str]:
        """Broadcast a message to all peers"""
        if not self.message_handler:
            logger.warning("Message handler not initialized")
            return None
            
        if not self.peer_discovery:
            logger.warning("Peer discovery not initialized")
            return None
            
        # Get addresses for all active peers
        addresses = [(peer.ip_address, self.DEFAULT_MESSAGING_PORT) 
                    for peer in self.peer_discovery.get_active_peers()]
                    
        if not addresses:
            logger.warning("No active peers to broadcast to")
            return None
            
        # Send broadcast message
        return self.message_handler.broadcast_message(
            content=content,
            addresses=addresses
        )
    
    def create_group(self, group_name: str, peer_ids: Optional[List[str]] = None) -> str:
        """
        Create a new message group.
        Returns the group ID.
        """
        group_id = f"group_{int(time.time())}_{hash(group_name) % 10000}"
        
        self.groups[group_id] = {
            "name": group_name,
            "created": time.time(),
            "members": peer_ids or []
        }
        
        self._save_config()
        logger.info(f"Created group: {group_name} ({group_id})")
        return group_id
    
    def add_to_group(self, group_id: str, peer_id: str) -> bool:
        """Add a peer to a group"""
        if group_id not in self.groups:
            logger.warning(f"Unknown group: {group_id}")
            return False
            
        if "members" not in self.groups[group_id]:
            self.groups[group_id]["members"] = []
            
        if peer_id not in self.groups[group_id]["members"]:
            self.groups[group_id]["members"].append(peer_id)
            self._save_config()
            logger.info(f"Added peer {peer_id} to group {self.groups[group_id]['name']}")
            return True
            
        return False
    
    def remove_from_group(self, group_id: str, peer_id: str) -> bool:
        """Remove a peer from a group"""
        if group_id not in self.groups:
            logger.warning(f"Unknown group: {group_id}")
            return False
            
        if "members" not in self.groups[group_id]:
            return False
            
        if peer_id in self.groups[group_id]["members"]:
            self.groups[group_id]["members"].remove(peer_id)
            self._save_config()
            logger.info(f"Removed peer {peer_id} from group {self.groups[group_id]['name']}")
            return True
            
        return False
    
    def delete_group(self, group_id: str) -> bool:
        """Delete a group"""
        if group_id not in self.groups:
            logger.warning(f"Unknown group: {group_id}")
            return False
            
        del self.groups[group_id]
        self._save_config()
        logger.info(f"Deleted group: {group_id}")
        return True
    
    def get_messages(self, peer_id: Optional[str] = None, group_id: Optional[str] = None, limit: int = 50) -> List[Message]:
        """Get message history"""
        if not self.message_handler:
            return []
            
        if peer_id:
            return self.message_handler.get_private_history(peer_id, limit)
        elif group_id:
            return self.message_handler.get_group_history(group_id, limit)
        else:
            return self.message_handler.get_message_history(limit)
    
    def clear_messages(self, peer_id: Optional[str] = None, group_id: Optional[str] = None) -> bool:
        """Clear message history"""
        if not self.message_handler:
            return False
            
        self.message_handler.clear_history(peer_id, group_id)
        return True
    
    # SSH methods
    
    def create_ssh_connection(self, 
                             host: str, 
                             port: int = 22, 
                             username: str = "", 
                             password: Optional[str] = None,
                             key_path: Optional[str] = None,
                             name: Optional[str] = None) -> Optional[str]:
        """
        Create a new SSH connection.
        Returns the connection ID if successful, None otherwise.
        """
        if not self.ssh_manager:
            logger.warning("SSH manager not initialized")
            return None
            
        return self.ssh_manager.create_connection(
            host=host,
            port=port,
            username=username,
            password=password,
            key_path=key_path,
            name=name
        )
    
    def get_ssh_connection(self, connection_id: str) -> Optional[SSHConnection]:
        """Get a specific SSH connection by ID"""
        if not self.ssh_manager:
            logger.warning("SSH manager not initialized")
            return None
            
        return self.ssh_manager.get_connection(connection_id)
    
    def get_all_ssh_connections(self) -> List[SSHConnection]:
        """Get all SSH connections"""
        if not self.ssh_manager:
            logger.warning("SSH manager not initialized")
            return []
            
        return self.ssh_manager.get_all_connections()
    
    def close_ssh_connection(self, connection_id: str) -> bool:
        """
        Close an SSH connection.
        Returns True if successful, False otherwise.
        """
        if not self.ssh_manager:
            logger.warning("SSH manager not initialized")
            return False
            
        return self.ssh_manager.close_connection(connection_id)
    
    def save_ssh_profile(self, name: str, host: str, port: int = 22, 
                        username: str = "", key_path: Optional[str] = None) -> str:
        """
        Save an SSH connection profile.
        Returns the profile ID.
        """
        if not self.ssh_manager:
            logger.warning("SSH manager not initialized")
            return ""
            
        return self.ssh_manager.save_profile(name, host, port, username, key_path)
    
    def delete_ssh_profile(self, profile_id: str) -> bool:
        """
        Delete an SSH profile.
        Returns True if successful, False otherwise.
        """
        if not self.ssh_manager:
            logger.warning("SSH manager not initialized")
            return False
            
        return self.ssh_manager.delete_profile(profile_id)
    
    def get_ssh_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific SSH profile by ID"""
        if not self.ssh_manager:
            logger.warning("SSH manager not initialized")
            return None
            
        return self.ssh_manager.get_profile(profile_id)
    
    def get_all_ssh_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get all SSH profiles"""
        if not self.ssh_manager:
            logger.warning("SSH manager not initialized")
            return {}
            
        return self.ssh_manager.get_all_profiles()
    
    def connect_from_ssh_profile(self, profile_id: str, password: Optional[str] = None) -> Optional[str]:
        """
        Create a connection from an SSH profile.
        Returns the connection ID if successful, None otherwise.
        """
        if not self.ssh_manager:
            logger.warning("SSH manager not initialized")
            return None
            
        return self.ssh_manager.connect_from_profile(profile_id, password)
    
    # Event listener methods
    
    def add_peer_listener(self, callback: Callable[[str, ZTalkPeer], None]):
        """
        Add a callback for peer events.
        Callback will receive event_type and peer object.
        """
        self.peer_listeners.append(callback)
        
    def remove_peer_listener(self, callback: Callable[[str, ZTalkPeer], None]):
        """Remove a peer event listener"""
        if callback in self.peer_listeners:
            self.peer_listeners.remove(callback)
            
    def add_message_listener(self, callback: Callable[[Message], None]):
        """
        Add a callback for message events.
        Callback will receive message object.
        """
        self.message_listeners.append(callback)
        
    def remove_message_listener(self, callback: Callable[[Message], None]):
        """Remove a message event listener"""
        if callback in self.message_listeners:
            self.message_listeners.remove(callback)
            
    def add_network_listener(self, callback: Callable[[Dict[str, str], Dict[str, str]], None]):
        """
        Add a callback for network change events.
        Callback will receive new_interfaces and old_interfaces.
        """
        self.network_listeners.append(callback)
        
    def remove_network_listener(self, callback: Callable[[Dict[str, str], Dict[str, str]], None]):
        """Remove a network change listener"""
        if callback in self.network_listeners:
            self.network_listeners.remove(callback)
    
    def add_ssh_listener(self, callback: Callable[[str, SSHConnection], None]):
        """
        Add a callback for SSH connection events.
        Callback will receive event_type and connection object.
        """
        self.ssh_listeners.append(callback)
        
    def remove_ssh_listener(self, callback: Callable[[str, SSHConnection], None]):
        """Remove an SSH connection listener"""
        if callback in self.ssh_listeners:
            self.ssh_listeners.remove(callback)
    
    # Private methods
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        os.makedirs(self.CONFIG_DIRECTORY, exist_ok=True)
        
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded configuration from {self.CONFIG_FILE}")
                    return config
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                
        # Default configuration
        default_config = {
            "username": os.environ.get("USER", "user"),
            "discovery_port": self.DEFAULT_DISCOVERY_PORT,
            "messaging_port": self.DEFAULT_MESSAGING_PORT,
            "groups": {},
            "dhcp_enabled": False,
            "dhcp_network": "192.168.100.0/24",
            "dhcp_server_ip": None,
            "theme": "dark"
        }
        
        logger.info(f"Created default configuration")
        return default_config
        
    def _save_config(self):
        """Save configuration to file"""
        try:
            # Create config directory if it doesn't exist
            if not os.path.exists(self.CONFIG_DIRECTORY):
                os.makedirs(self.CONFIG_DIRECTORY, exist_ok=True)
                
            # Update config with current values
            self.config["username"] = self.username
            self.config["groups"] = self.groups
            
            # Save to file
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def _on_peer_event(self, event_type: str, peer: ZTalkPeer):
        """Handle peer discovery events"""
        # Forward to listeners
        for callback in self.peer_listeners:
            try:
                callback(event_type, peer)
            except Exception as e:
                logger.error(f"Error in peer listener: {e}")
    
    def _on_message_received(self, message: Message):
        """Handle incoming messages"""
        # Forward to listeners
        for callback in self.message_listeners:
            try:
                callback(message)
            except Exception as e:
                logger.error(f"Error in message listener: {e}")
                
    def _on_network_change(self, new_interfaces: Dict[str, str], old_interfaces: Dict[str, str]):
        """Handle network interface changes"""
        # Forward to listeners
        for callback in self.network_listeners:
            try:
                callback(new_interfaces, old_interfaces)
            except Exception as e:
                logger.error(f"Error in network listener: {e}")
    
    # DHCP Management Methods
    def _start_dhcp_server(self) -> bool:
        """Initialize and start the DHCP server"""
        try:
            # Create DHCP server instance
            self.dhcp_server = DHCPServer(self.network_manager)
            
            # Configure with settings from config
            success = self.dhcp_server.configure(
                network=self.dhcp_network,
                server_ip=self.dhcp_server_ip,
                # Optional additional settings can be added here
            )
            
            if not success:
                logger.error("Failed to configure DHCP server")
                return False
                
            # Start the DHCP server
            if not self.dhcp_server.start():
                logger.error("Failed to start DHCP server")
                return False
                
            logger.info(f"DHCP server started successfully on network {self.dhcp_network}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting DHCP server: {e}")
            return False
            
    def enable_dhcp(self, enable: bool, network: Optional[str] = None, 
                  server_ip: Optional[str] = None) -> bool:
        """
        Enable or disable the DHCP server functionality.
        
        Args:
            enable: True to enable, False to disable
            network: Network in CIDR notation (e.g., "192.168.100.0/24")
            server_ip: IP address for the DHCP server
            
        Returns:
            True if successful, False otherwise
        """
        # Update configuration
        self.dhcp_enabled = enable
        self.config["dhcp_enabled"] = enable
        
        if network:
            self.dhcp_network = network
            self.config["dhcp_network"] = network
            
        if server_ip:
            self.dhcp_server_ip = server_ip
            self.config["dhcp_server_ip"] = server_ip
            
        # Save updated configuration
        self._save_config()
        
        # If enabling and already running, start DHCP server
        if enable and self.running:
            # Stop existing server if running
            if self.dhcp_server:
                self.dhcp_server.stop()
                
            # Start with new configuration
            return self._start_dhcp_server()
            
        # If disabling and server is running, stop it
        elif not enable and self.dhcp_server:
            self.dhcp_server.stop()
            self.dhcp_server = None
            logger.info("DHCP server disabled")
            
        return True
        
    def get_dhcp_status(self) -> Dict[str, Any]:
        """
        Get current DHCP server status and configuration.
        
        Returns:
            Dictionary with DHCP status and configuration
        """
        status = {
            "enabled": self.dhcp_enabled,
            "running": bool(self.dhcp_server and self.running),
            "network": self.dhcp_network,
            "server_ip": self.dhcp_server_ip,
        }
        
        # Add lease information if server is running
        if self.dhcp_server:
            status["leases"] = self.dhcp_server.get_leases()
            
        return status 