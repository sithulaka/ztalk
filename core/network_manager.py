import socket
import threading
import time
import netifaces
import random
import os
from typing import Callable, Optional, List

class NetworkManager:
    def __init__(self):
        self.current_interface: Optional[str] = None
        self.listeners: List[Callable] = []
        self.running: bool = True
        self._monitor_thread: threading.Thread = threading.Thread(target=self._interface_monitor)
        self.check_interval: int = 5  # seconds

    def start(self) -> None:
        """Start the network monitoring thread"""
        self._monitor_thread.start()

    def stop(self) -> None:
        """Stop the network monitoring"""
        self.running = False
        self._monitor_thread.join()

    def add_interface_change_listener(self, callback: Callable) -> None:
        """Add a callback for network change events"""
        self.listeners.append(callback)

    def get_active_interface_ip(self) -> Optional[str]:
        """
        Get the first available IPv4 address.
        If none exists, automatically assigns a link-local address (169.254.x.x).
        """
        try:
            # First try normal detection
            if ip := self._get_normal_ip():
                return ip
                
            # If no IP found, assign link-local address
            return self._assign_link_local_ip()
        except Exception as e:
            print(f"[Network Error] IP detection failed: {e}")
            return None

    def validate_network(self) -> bool:
        """Check if any network interface is available"""
        return self.get_active_interface_ip() is not None

    def _get_normal_ip(self) -> Optional[str]:
        """Check physical interfaces for existing IPv4 addresses"""
        # Explicitly check known physical interfaces first
        for interface in ['enP3p49s0', 'enP4p65s0', 'wlP2p33s0']:
            try:
                addrs = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
                for addr in addrs:
                    if 'addr' in addr and not addr['addr'].startswith(('127.', '169.254.')):
                        return addr['addr']
            except ValueError:
                continue
                
        return None

    def _assign_link_local_ip(self) -> Optional[str]:
        """
        Assign a Bonjour-style link-local IP address (RFC 3927)
        Returns the assigned IP or None if failed
        """
        interface = self._find_physical_interface()
        if not interface:
            print("[Network] No physical interface available for link-local assignment")
            return None

        # Generate random IP in 169.254.0.0/16 range (excluding .0 and .255)
        ip = f"169.254.{random.randint(1, 254)}.{random.randint(1, 254)}"
        
        try:
            # Assign the IP address
            os.system(f"sudo ip addr add {ip}/16 dev {interface} >/dev/null 2>&1")
            os.system(f"sudo ip link set {interface} up >/dev/null 2>&1")
            print(f"[Network] Assigned link-local IP: {ip} to {interface}")
            return ip
        except Exception as e:
            print(f"[Network Error] Failed to assign link-local IP: {e}")
            return None

    def _find_physical_interface(self) -> Optional[str]:
        """Find the first active physical interface without an IPv4 address"""
        # List of common virtual interface prefixes to exclude
        VIRTUAL_PREFIXES = ('docker', 'veth', 'br-', 'virbr', 'lo')
        
        for interface in netifaces.interfaces():
            # Skip virtual interfaces
            if any(interface.startswith(prefix) for prefix in VIRTUAL_PREFIXES):
                continue
                
            # Check interface flags to ensure it's a physical interface
            try:
                flags = netifaces.ifaddresses(interface).get(netifaces.AF_LINK, [{}])[0].get('flags', 0)
                
                # Skip interfaces that are not UP or don't have a carrier
                if not (flags & netifaces.IFF_UP) or (flags & netifaces.IFF_NOARP):
                    continue
                    
            except (ValueError, KeyError):
                continue
                
            # Skip interfaces without IPv4 support
            if netifaces.AF_INET not in netifaces.ifaddresses(interface):
                continue
                
            # Prefer interfaces with actual link (carrier)
            addrs = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
            if not any(addr.get('addr', '').startswith('169.254') for addr in addrs):
                return interface
                
        return None


    def _interface_monitor(self) -> None:
        """Monitor network interfaces for changes"""
        last_ip = self.get_active_interface_ip()
        while self.running:
            current_ip = self.get_active_interface_ip()
            
            if current_ip != last_ip:
                print(f"[Network] IP changed from {last_ip} to {current_ip}")
                last_ip = current_ip
                for callback in self.listeners:
                    try:
                        callback(current_ip)
                    except Exception as e:
                        print(f"[Network Error] Listener failed: {e}")
            
            time.sleep(self.check_interval)