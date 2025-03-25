import socket
import logging
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
import asyncio
from typing import Dict, Optional

class ServiceDiscovery(ServiceListener):
    def __init__(self, network_manager):
        self.logger = logging.getLogger('ServiceDiscovery')
        self.network_manager = network_manager
        self.zeroconf: Optional[Zeroconf] = None
        self.browser = None
        self.peers: Dict[str, tuple] = {}
        self.service_type = "_ztalk._tcp.local."
        self.service_info = None
        self._setup_event_loop()

    def _setup_event_loop(self):
        """Setup dedicated event loop for zeroconf"""
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        except Exception as e:
            self.logger.error(f"Failed to setup event loop: {e}")

    def register_service(self, username: str, port: int) -> bool:
        """Register service on all active interfaces"""
        try:
            if not self.zeroconf:
                self.zeroconf = Zeroconf()

            ips = list(self.network_manager.get_all_active_ips())
            if not ips:
                self.logger.error("No active interfaces found")
                return False

            addresses = [socket.inet_aton(ip) for ip in ips]
            
            self.service_info = ServiceInfo(
                self.service_type,
                f"{username}.{self.service_type}",
                addresses=addresses,
                port=port,
                properties={b'user': username.encode()}
            )
            
            self.zeroconf.register_service(self.service_info)
            self.browse_services()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register service: {e}")
            return False

    def browse_services(self):
        ServiceBrowser(self.zeroconf, self.service_type, self)

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info and info.addresses:
            addr = socket.inet_ntoa(info.addresses[0])
            user = info.properties.get(b'user', b'unknown').decode()
            self.peers[user] = (addr, info.port)
            print(f"\n[+] Discovered {user} at {addr}:{info.port}")

    def remove_service(self, zc, type_, name):
        user = name.split('.')[0]
        if user in self.peers:
            del self.peers[user]
            print(f"\n[-] {user} left")

    def update_service(self, zc, type_, name):
        pass

    def shutdown(self):
        """Clean shutdown of zeroconf services"""
        try:
            if self.service_info and self.zeroconf:
                try:
                    self.zeroconf.unregister_service(self.service_info)
                except Exception as e:
                    self.logger.error(f"Error unregistering service: {e}")
                    
            if self.zeroconf:
                try:
                    self.zeroconf.close()
                except Exception as e:
                    self.logger.error(f"Error closing zeroconf: {e}")
                    
            if self._loop:
                try:
                    self._loop.stop()
                    self._loop.close()
                except Exception as e:
                    self.logger.error(f"Error closing event loop: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error in shutdown: {e}")