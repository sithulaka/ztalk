import socket
import threading
import time
import netifaces
import random
import os
from typing import Callable, Optional, Dict, List

class NetworkManager:
    def __init__(self):
        self.active_interfaces: Dict[str, str] = {}  # {interface_name: ip}
        self.listeners: List[Callable] = []
        self.running = True
        self._monitor_thread = threading.Thread(target=self._interface_monitor)
        self.check_interval = 5  # seconds

    def start(self):
        """Start monitoring network interfaces"""
        self._update_interfaces()
        self._monitor_thread.start()

    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)

    def validate_network(self) -> bool:
        """Check if we have any active network interfaces"""
        return len(self.active_interfaces) > 0

    def add_interface_change_listener(self, callback: Callable):
        """Add callback for interface changes"""
        self.listeners.append(callback)

    def get_all_active_ips(self) -> List[str]:
        """Get IPs from all active physical interfaces"""
        return list(self.active_interfaces.values())

    def get_primary_ip(self) -> Optional[str]:
        """Get preferred IP (Ethernet first)"""
        for interface, ip in self.active_interfaces.items():
            if interface.startswith(('en', 'eth')):
                return ip
        return next(iter(self.active_interfaces.values()), None) if self.active_interfaces else None

    def _update_interfaces(self):
        """Refresh active interface list"""
        new_interfaces = {}
        for interface in netifaces.interfaces():
            if self._is_physical_interface(interface):
                if ip := self._get_interface_ip(interface):
                    new_interfaces[interface] = ip
        
        if new_interfaces != self.active_interfaces:
            self.active_interfaces = new_interfaces
            for callback in self.listeners:
                callback(self.active_interfaces)

    def _is_physical_interface(self, interface: str) -> bool:
        """Identify physical network interfaces"""
        return (interface.startswith(('en', 'eth', 'wl')) and not any(
            v in interface for v in ['docker', 'virbr', 'veth', 'lo']))

    def _get_interface_ip(self, interface: str) -> Optional[str]:
        """Get IPv4 address for specific interface"""
        try:
            # First check for any IPv4 address
            addrs = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
            for addr in addrs:
                if 'addr' in addr and not addr['addr'].startswith('127.'):
                    return addr['addr']
            
            # If no IP found, check interface status using system calls
            with open(f'/sys/class/net/{interface}/operstate') as f:
                if 'up' in f.read().lower():
                    return self._assign_link_local_ip(interface)
                    
        except (ValueError, KeyError, IOError):
            pass
        return None

    def _assign_link_local_ip(self, interface: str) -> Optional[str]:
        """Assign Bonjour-style link-local address"""
        ip = f"192.168.1.{random.randint(2,254)}"
        try:
            os.system(f"sudo ip addr add {ip}/24 dev {interface} >/dev/null 2>&1")
            os.system(f"sudo ip link set {interface} up >/dev/null 2>&1")
            return ip
        except Exception:
            return None

    def _interface_monitor(self):
        """Monitor for network changes"""
        while self.running:
            self._update_interfaces()
            time.sleep(self.check_interval)