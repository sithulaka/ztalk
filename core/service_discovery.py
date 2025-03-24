from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
import socket
from typing import Dict

class ServiceDiscovery(ServiceListener):
    def __init__(self, network_manager):
        self.network_manager = network_manager
        self.zeroconf = Zeroconf()
        self.peers: Dict[str, tuple] = {}  # {username: (ip, port)}
        self.service_type = "_message._tcp.local."
        self.service_info = None

    def register_service(self, username: str, port: int):
        """Register service on all active interfaces"""
        ips = [socket.inet_aton(ip) for ip in self.network_manager.get_all_active_ips()]
        
        self.service_info = ServiceInfo(
            self.service_type,
            f"{username}.{self.service_type}",
            addresses=ips,
            port=port,
            properties={b'user': username.encode()},
        )
        self.zeroconf.register_service(self.service_info)
        self.browse_services()

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
        if self.service_info:
            self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()