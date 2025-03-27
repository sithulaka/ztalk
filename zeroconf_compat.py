#!/usr/bin/env python3
"""
Zeroconf compatibility module for ZTalk

This module provides compatibility for the zeroconf module, which may not be
properly installed in some environments. It attempts to import the original
zeroconf module, and if that fails, it provides a minimal implementation
for local network discovery.
"""

import sys
import socket
import threading
import time
import random
import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Callable, Union, Set, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('zeroconf_compat')

# Try to import the real zeroconf module
try:
    from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, InterfaceChoice
    logger.info("Using real zeroconf module")
    
    # No need to define anything else, we'll just use the real module
    real_zeroconf = True

except ImportError:
    logger.warning("Could not import zeroconf, using fallback implementation")
    real_zeroconf = False
    
    # Define minimal compatibility classes for zeroconf
    class ServiceInfo:
        """
        Simple ServiceInfo class for storing service information
        """
        def __init__(self, type_: str, name: str, addresses=None, port: int = None, 
                    weight: int = 0, priority: int = 0, properties: Dict = None, server: str = None):
            """
            Initialize a service info object
            
            Args:
                type_: Service type, e.g. '_http._tcp.local.'
                name: Service name, e.g. 'My Service._http._tcp.local.'
                addresses: List of IP addresses
                port: Service port
                weight: Service weight
                priority: Service priority
                properties: Service properties (key-value pairs)
                server: Server hostname
            """
            self.type = type_
            self.name = name
            self._addresses = addresses or []
            self.port = port or 0
            self.weight = weight
            self.priority = priority
            self.server = server or socket.gethostname()
            self.properties = properties or {}
        
        def addresses(self):
            """Get the addresses of this service"""
            return self._addresses
        
        @staticmethod
        def from_dict(data: Dict) -> 'ServiceInfo':
            """Create a ServiceInfo from a dictionary"""
            return ServiceInfo(
                type_=data.get('type', ''),
                name=data.get('name', ''),
                addresses=data.get('addresses', []),
                port=data.get('port', 0),
                weight=data.get('weight', 0),
                priority=data.get('priority', 0),
                properties=data.get('properties', {}),
                server=data.get('server', '')
            )
        
        def to_dict(self) -> Dict:
            """Convert to a dictionary for serialization"""
            return {
                'type': self.type,
                'name': self.name,
                'addresses': self._addresses,
                'port': self.port,
                'weight': self.weight,
                'priority': self.priority,
                'server': self.server,
                'properties': self.properties
            }
    
    class InterfaceChoice:
        """Enum-like class for interface choices"""
        All = 0
        Default = 1
        
    class ServiceBrowser:
        """
        Simple service browser for discovery on local network
        """
        def __init__(self, zeroconf: 'Zeroconf', type_: str, handlers=None):
            """
            Initialize a service browser
            
            Args:
                zeroconf: Zeroconf instance
                type_: Service type to browse for
                handlers: List of handler functions to call when services are found
            """
            self.zeroconf = zeroconf
            self.type = type_
            self.handlers = handlers or []
            self._stop = False
            
            # Start the browser thread
            self._thread = threading.Thread(target=self._browse, daemon=True)
            self._thread.start()
        
        def _browse(self):
            """Background thread for service discovery"""
            while not self._stop:
                try:
                    # Let the zeroconf instance handle discovery
                    self.zeroconf._send_discovery_request(self.type)
                    
                    # Sleep to avoid excessive traffic
                    time.sleep(random.uniform(10, 15))
                except Exception as e:
                    logger.error(f"Error in service browser: {e}")
                    time.sleep(5)
        
        def cancel(self):
            """Stop the browser"""
            self._stop = True
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
    
    class Zeroconf:
        """
        Simple Zeroconf implementation using UDP broadcasts
        """
        # UDP broadcast port for our custom discovery
        DISCOVERY_PORT = 5353  # Same as mDNS
        
        def __init__(self, interfaces=InterfaceChoice.All):
            """
            Initialize a Zeroconf instance
            
            Args:
                interfaces: Which interfaces to use
            """
            self.interfaces = interfaces
            self._services: Dict[str, ServiceInfo] = {}
            self._browsers: List[ServiceBrowser] = []
            self._handlers: Dict[str, List[Callable]] = {}
            self._stop = False
            
            # Create a unique instance ID
            self._instance_id = str(uuid.uuid4())
            
            # Start UDP discovery sockets
            self._setup_sockets()
            
            # Start listener thread
            self._thread = threading.Thread(target=self._listen, daemon=True)
            self._thread.start()
        
        def _setup_sockets(self):
            """Set up UDP sockets for discovery"""
            try:
                # Create a UDP socket for broadcasting
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                
                # Bind to all interfaces
                try:
                    self._sock.bind(('', self.DISCOVERY_PORT))
                except OSError:
                    # If we can't bind to the port, use a random port
                    self._sock.bind(('', 0))
                    logger.warning(f"Could not bind to port {self.DISCOVERY_PORT}, using random port")
                
                # Set a timeout for recvfrom
                self._sock.settimeout(0.5)
                
                logger.info(f"Zeroconf compatible service started on port {self._sock.getsockname()[1]}")
            except Exception as e:
                logger.error(f"Error setting up discovery sockets: {e}")
                # Create a dummy socket for sending only
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        def _listen(self):
            """Listen for discovery packets"""
            while not self._stop:
                try:
                    # Receive a discovery packet
                    data, addr = self._sock.recvfrom(4096)
                    
                    # Ignore packets from ourselves
                    if data.startswith(b'ZTALK-DISCOVER'):
                        # Basic discovery packet
                        try:
                            # Parse the packet
                            parts = data.decode('utf-8').split(':', 4)
                            if len(parts) >= 4:
                                cmd = parts[0]  # ZTALK-DISCOVER
                                sender_id = parts[1]
                                
                                # Don't process our own packets
                                if sender_id == self._instance_id:
                                    continue
                                
                                service_type = parts[2]
                                request_type = parts[3]
                                
                                if request_type == 'QUERY':
                                    # Someone is looking for services
                                    self._respond_to_query(service_type, addr)
                                elif request_type == 'ANNOUNCE':
                                    # Someone is announcing a service
                                    if len(parts) >= 5:
                                        service_data = json.loads(parts[4])
                                        service_info = ServiceInfo.from_dict(service_data)
                                        
                                        # Add to our known services
                                        self._add_service(service_type, service_info.name, service_info)
                        except Exception as e:
                            logger.error(f"Error processing discovery packet: {e}")
                except socket.timeout:
                    # This is expected, just continue
                    pass
                except OSError as e:
                    if self._stop:
                        break
                    logger.error(f"Socket error: {e}")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error in discovery listener: {e}")
                    time.sleep(1)
        
        def _respond_to_query(self, service_type: str, addr: Tuple[str, int]):
            """Respond to a service query"""
            # Check if we have any services of this type
            our_services = [s for s in self._services.values() 
                          if s.type == service_type]
            
            # Send a response for each service
            for service in our_services:
                try:
                    announce_packet = f"ZTALK-DISCOVER:{self._instance_id}:{service_type}:ANNOUNCE:{json.dumps(service.to_dict())}"
                    self._sock.sendto(announce_packet.encode('utf-8'), addr)
                except Exception as e:
                    logger.error(f"Error sending service announcement: {e}")
        
        def _send_discovery_request(self, service_type: str):
            """Send a discovery request for a service type"""
            try:
                # Create a discovery packet
                query_packet = f"ZTALK-DISCOVER:{self._instance_id}:{service_type}:QUERY"
                
                # Send to broadcast address
                self._sock.sendto(query_packet.encode('utf-8'), ('<broadcast>', self.DISCOVERY_PORT))
            except Exception as e:
                logger.error(f"Error sending discovery request: {e}")
        
        def _add_service(self, service_type: str, service_name: str, service_info: ServiceInfo):
            """Add a discovered service"""
            key = f"{service_name}.{service_type}"
            if key not in self._services:
                self._services[key] = service_info
                
                # Notify handlers
                for handler in self._handlers.get(service_type, []):
                    try:
                        handler.add_service(self, service_type, service_name)
                    except Exception as e:
                        logger.error(f"Error in service handler: {e}")
        
        def register_service(self, info: ServiceInfo):
            """Register a service for broadcasting"""
            key = f"{info.name}.{info.type}"
            self._services[key] = info
            
            # Announce the service
            try:
                announce_packet = f"ZTALK-DISCOVER:{self._instance_id}:{info.type}:ANNOUNCE:{json.dumps(info.to_dict())}"
                self._sock.sendto(announce_packet.encode('utf-8'), ('<broadcast>', self.DISCOVERY_PORT))
            except Exception as e:
                logger.error(f"Error announcing service: {e}")
        
        def unregister_service(self, info: ServiceInfo):
            """Unregister a service"""
            key = f"{info.name}.{info.type}"
            if key in self._services:
                del self._services[key]
        
        def add_service_listener(self, service_type: str, listener: Any):
            """Add a service listener"""
            if service_type not in self._handlers:
                self._handlers[service_type] = []
            self._handlers[service_type].append(listener)
        
        def remove_service_listener(self, listener: Any):
            """Remove a service listener"""
            for handlers in self._handlers.values():
                if listener in handlers:
                    handlers.remove(listener)
        
        def get_service_info(self, service_type: str, service_name: str) -> Optional[ServiceInfo]:
            """Get information about a service"""
            key = f"{service_name}.{service_type}"
            return self._services.get(key)
        
        def close(self):
            """Close the Zeroconf instance"""
            self._stop = True
            try:
                self._sock.close()
            except:
                pass
            
            # Wait for the thread to finish
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)

# Export a function to check if we're using the fallback implementation
def is_fallback() -> bool:
    """Check if we're using the fallback implementation"""
    return not real_zeroconf

# Test implementation
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    print(f"Using fallback implementation: {is_fallback()}")
    
    if is_fallback():
        print("\nTesting fallback implementation...")
        
        # Define a simple handler
        class ServiceListener:
            def add_service(self, zeroconf, service_type, name):
                print(f"Service added: {name}")
                info = zeroconf.get_service_info(service_type, name)
                if info:
                    print(f"  Info: {info.to_dict()}")
            
            def remove_service(self, zeroconf, service_type, name):
                print(f"Service removed: {name}")
        
        # Create a zeroconf instance
        zc = Zeroconf()
        
        # Create a service info
        info = ServiceInfo(
            type_="_ztalk._tcp.local.",
            name="Test Service._ztalk._tcp.local.",
            addresses=["192.168.1.100"],
            port=8080,
            properties={"username": "Test User"}
        )
        
        # Register the service
        zc.register_service(info)
        
        # Start browsing for services
        listener = ServiceListener()
        browser = ServiceBrowser(zc, "_ztalk._tcp.local.", [listener])
        
        try:
            print("Browsing for services (30 seconds)...")
            time.sleep(30)
        finally:
            browser.cancel()
            zc.close()
    else:
        print("\nUsing real zeroconf implementation") 