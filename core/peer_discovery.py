"""
Peer Discovery Module for ZTalk

This module handles peer discovery on local networks using mDNS/Zeroconf.
"""

import sys
import os
import time
import threading
import socket
import logging
import json
import uuid
import platform
from typing import Dict, List, Callable, Optional, Any, Set

# Import the zeroconf compatibility module instead of zeroconf directly
try:
    # First try to import from our compatibility module
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from zeroconf_compat import ServiceInfo, Zeroconf, ServiceBrowser, is_fallback
    if is_fallback():
        logging.info("Using fallback zeroconf implementation")
    else:
        logging.info("Using real zeroconf implementation")
except ImportError:
    # If that fails, try to import zeroconf directly
    try:
        from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser
        logging.info("Using direct zeroconf import")
    except ImportError:
        logging.error("Failed to import zeroconf or zeroconf_compat")
        raise

from core.network_manager import NetworkManager

# Configure logging
logger = logging.getLogger(__name__)

class ZTalkPeer:
    """Represents a discovered peer on the network"""
    
    def __init__(self, 
                 peer_id: str, 
                 name: str, 
                 ip_address: str, 
                 port: int, 
                 properties: Dict[str, Any] = None):
        self.peer_id = peer_id  # Unique identifier
        self.name = name  # Display name
        self.ip_address = ip_address
        self.port = port
        self.last_seen = time.time()
        self.is_active = True
        self.properties = properties or {}
        self.latency = None  # Latency in ms (optional)
        
    def __eq__(self, other):
        if not isinstance(other, ZTalkPeer):
            return False
        return self.peer_id == other.peer_id
        
    def __hash__(self):
        return hash(self.peer_id)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "peer_id": self.peer_id,
            "name": self.name,
            "ip_address": self.ip_address,
            "port": self.port,
            "last_seen": self.last_seen,
            "is_active": self.is_active,
            "properties": self.properties,
            "latency": self.latency
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ZTalkPeer':
        """Create peer from dictionary"""
        peer = cls(
            peer_id=data["peer_id"],
            name=data["name"],
            ip_address=data["ip_address"],
            port=data["port"],
            properties=data.get("properties", {})
        )
        peer.last_seen = data.get("last_seen", time.time())
        peer.is_active = data.get("is_active", True)
        peer.latency = data.get("latency")
        return peer

        
class PeerDiscovery:
    """
    Handles peer discovery using Zeroconf/mDNS to automatically find 
    other ZTalk instances on the local network.
    """
    
    # ZTalk service type definition
    SERVICE_TYPE = "_ztalk._tcp.local."
    
    def __init__(self, network_manager: NetworkManager, port: int = 8989):
        # Core components
        self.network_manager = network_manager
        self.port = port
        
        # Peer tracking
        self.peers: Dict[str, ZTalkPeer] = {}  # peer_id -> ZTalkPeer
        self.peer_listeners: List[Callable[[str, ZTalkPeer], None]] = []  # Callbacks for peer events
        
        # Create a unique identifier for this instance
        self.instance_id = str(uuid.uuid4())
        
        # User identity
        self.hostname = socket.gethostname()
        try:
            self.username = platform.node() or self.hostname.split('.')[0] 
        except Exception:
            self.username = self.hostname
            
        # Zeroconf components
        self.zeroconf = None
        self.browser = None
        self.info = None
        self.registered = False
        
        # Peer status checking
        self.running = True
        self.status_thread = threading.Thread(target=self._check_peer_status, daemon=True)
        self.check_interval = 30  # seconds
        
        # Network interface change callback
        self.network_manager.add_interface_change_listener(self._on_interface_change)
        
    def start(self):
        """
        Start the peer discovery service, registering this instance and 
        searching for other instances on the network.
        """
        # Set up zeroconf
        self.zeroconf = Zeroconf()
        
        # Register our service
        self._register_service()
        
        # Start discovering peers
        self.browser = ServiceBrowser(self.zeroconf, self.SERVICE_TYPE, self)
        
        # Start status checking thread
        self.status_thread.start()
        
        logger.info(f"Peer discovery started: {self.username} ({self.instance_id})")
        return True
        
    def stop(self):
        """Stop peer discovery and unregister service"""
        self.running = False
        
        # Clean up zeroconf
        if self.zeroconf:
            if self.registered and self.info:
                self.zeroconf.unregister_service(self.info)
                self.registered = False
            
            self.zeroconf.close()
            self.zeroconf = None
            
        # Wait for status thread to end
        if self.status_thread.is_alive():
            self.status_thread.join(timeout=1.0)
            
        # Remove network manager callback
        self.network_manager.remove_interface_change_listener(self._on_interface_change)
        
        logger.info("Peer discovery stopped")
        return True
        
    def add_peer_listener(self, callback: Callable[[str, ZTalkPeer], None]):
        """
        Add a callback for peer events.
        Callback will receive event_type (added/updated/removed) and the peer object.
        """
        self.peer_listeners.append(callback)
        
    def remove_peer_listener(self, callback: Callable[[str, ZTalkPeer], None]):
        """Remove a peer event listener"""
        if callback in self.peer_listeners:
            self.peer_listeners.remove(callback)
            
    def get_all_peers(self) -> List[ZTalkPeer]:
        """Get all discovered peers"""
        return list(self.peers.values())
    
    def get_active_peers(self) -> List[ZTalkPeer]:
        """Get only active peers"""
        return [peer for peer in self.peers.values() if peer.is_active]
        
    def get_peer(self, peer_id: str) -> Optional[ZTalkPeer]:
        """Get a specific peer by ID"""
        return self.peers.get(peer_id)
    
    def update_username(self, new_username: str):
        """Update this instance's displayed username"""
        self.username = new_username
        
        # Re-register service with new username
        if self.zeroconf and self.registered:
            self._register_service()
    
    # ==== Zeroconf service handlers ====
    
    def add_service(self, zeroconf, service_type, name):
        """Called by Zeroconf when a new service is discovered"""
        try:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                # Extract peer information
                ip_address = socket.inet_ntoa(info.addresses[0]) if info.addresses else "0.0.0.0"
                port = info.port
                
                # Extract properties
                properties = {}
                for key, value in info.properties.items():
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    properties[key] = value
                
                # Get peer ID and username
                peer_id = properties.get('id', str(uuid.uuid4()))
                username = properties.get('username', name.split('.')[0])
                
                # Skip our own instance
                if peer_id == self.instance_id:
                    return
                
                # Create or update peer
                if peer_id in self.peers:
                    peer = self.peers[peer_id]
                    peer.ip_address = ip_address
                    peer.port = port
                    peer.name = username
                    peer.last_seen = time.time()
                    peer.is_active = True
                    peer.properties = properties
                    self._notify_peer_listeners("updated", peer)
                else:
                    peer = ZTalkPeer(peer_id, username, ip_address, port, properties)
                    self.peers[peer_id] = peer
                    self._notify_peer_listeners("added", peer)
                
                logger.debug(f"Discovered peer: {username} ({ip_address}:{port})")
        except Exception as e:
            logger.error(f"Error adding service: {e}")
    
    def remove_service(self, zeroconf, service_type, name):
        """Called by Zeroconf when a service is removed"""
        try:
            # Find the peer with this service name
            for peer_id, peer in list(self.peers.items()):
                if peer.name in name:
                    peer.is_active = False
                    self._notify_peer_listeners("removed", peer)
                    logger.debug(f"Peer removed: {peer.name} ({peer.ip_address})")
        except Exception as e:
            logger.error(f"Error removing service: {e}")
    
    def update_service(self, zeroconf, service_type, name):
        """Called by Zeroconf when a service is updated"""
        self.add_service(zeroconf, service_type, name)
    
    # ==== Private methods ====
    
    def _register_service(self):
        """Register this instance as a ZTalk service"""
        try:
            # Get our IP address
            ip_address = self.network_manager.get_primary_ip()
            if not ip_address:
                logger.warning("No IP address available for service registration")
                return False
                
            # Unregister existing service if it exists
            if self.registered and self.info:
                self.zeroconf.unregister_service(self.info)
                self.registered = False
                
            # Create properties dict
            properties = {
                'id': self.instance_id,
                'username': self.username,
                'version': '1.0.0',  # Application version
                'platform': platform.system()
            }
            
            # Convert properties to bytes as required by zeroconf
            bytes_properties = {}
            for k, v in properties.items():
                bytes_properties[k.encode('utf-8')] = str(v).encode('utf-8')
            
            # Create service info
            self.info = ServiceInfo(
                self.SERVICE_TYPE,
                f"{self.username}.{self.SERVICE_TYPE}",
                addresses=[socket.inet_aton(ip_address)],
                port=self.port,
                properties=bytes_properties
            )
            
            # Register the service
            self.zeroconf.register_service(self.info)
            self.registered = True
            
            logger.info(f"Registered service: {self.username} at {ip_address}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering service: {e}")
            return False
    
    def _check_peer_status(self):
        """Periodic check of peer status"""
        while self.running:
            try:
                current_time = time.time()
                timeout_threshold = 90  # seconds
                
                # Check each peer's last seen time
                for peer_id, peer in list(self.peers.items()):
                    if peer.is_active and (current_time - peer.last_seen) > timeout_threshold:
                        # Peer hasn't been seen for a while, mark as inactive
                        peer.is_active = False
                        self._notify_peer_listeners("timeout", peer)
                        logger.debug(f"Peer timed out: {peer.name} ({peer.ip_address})")
            except Exception as e:
                logger.error(f"Error checking peer status: {e}")
                
            # Sleep for the check interval
            time.sleep(self.check_interval)
    
    def _notify_peer_listeners(self, event_type: str, peer: ZTalkPeer):
        """Notify all registered listeners about peer events"""
        for callback in self.peer_listeners:
            try:
                callback(event_type, peer)
            except Exception as e:
                logger.error(f"Error in peer listener callback: {e}")
    
    def _on_interface_change(self, new_interfaces, old_interfaces):
        """Called when network interfaces change"""
        # Re-register service when network changes
        if self.zeroconf:
            self._register_service() 