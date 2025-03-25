import socket
import threading
import time
import netifaces
import random
import os
import platform
import subprocess
import ipaddress
from typing import Callable, Optional, Dict, List, Set, Tuple

class NetworkManager:
    def __init__(self):
        self.active_interfaces: Dict[str, str] = {}  # {interface_name: ip}
        self.network_segments: Dict[str, List[str]] = {}  # {network_prefix: [ips]}
        self.listeners: List[Callable] = []
        self.running = True
        self._monitor_thread = threading.Thread(target=self._interface_monitor, daemon=True)
        self.check_interval = 5  # seconds
        self.platform = platform.system()  # 'Windows', 'Darwin' (macOS), or 'Linux'
        # Track ARP table for cross-subnet communication
        self.arp_table: Dict[str, Dict[str, str]] = {}  # {network: {ip: mac}}
        # Track available network bridges
        self.bridges: Set[str] = set()

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

    def get_network_segments(self) -> Dict[str, List[str]]:
        """Get available network segments"""
        return self.network_segments

    def get_primary_ip(self) -> Optional[str]:
        """Get preferred IP (Ethernet first)"""
        # Platform-specific primary interface patterns
        if self.platform == "Windows":
            primary_patterns = ('Ethernet', 'Wi-Fi')
        elif self.platform == "Darwin":  # macOS
            primary_patterns = ('en0', 'en1')
        else:  # Linux
            primary_patterns = ('en', 'eth', 'wl')
            
        for pattern in primary_patterns:
            for interface, ip in self.active_interfaces.items():
                if interface.startswith(pattern):
                    return ip
                    
        return next(iter(self.active_interfaces.values()), None) if self.active_interfaces else None

    def create_virtual_bridge(self, interface1: str, interface2: str) -> bool:
        """Create a virtual bridge between two interfaces to enable cross-network communication"""
        bridge_name = f"br_{interface1}_{interface2}"
        
        try:
            if self.platform == "Linux":
                # Check if bridge-utils is installed
                result = subprocess.run(['which', 'brctl'], capture_output=True, text=True)
                if result.returncode != 0:
                    print("bridge-utils not installed. Cannot create bridge.")
                    return False
                
                # Create bridge
                os.system(f"sudo brctl addbr {bridge_name}")
                os.system(f"sudo brctl addif {bridge_name} {interface1}")
                os.system(f"sudo brctl addif {bridge_name} {interface2}")
                os.system(f"sudo ip link set {bridge_name} up")
                
                self.bridges.add(bridge_name)
                return True
            elif self.platform == "Darwin":  # macOS
                # macOS uses different bridging commands
                os.system(f"sudo ifconfig bridge create")
                os.system(f"sudo ifconfig bridge0 addm {interface1} addm {interface2} up")
                self.bridges.add("bridge0")
                return True
            elif self.platform == "Windows":
                # Windows bridging requires more complex approach using netsh or PowerShell
                # This is a simplified version
                os.system(f'netsh interface bridge add interface "{interface1}" "{interface2}"')
                return True
                
        except Exception as e:
            print(f"Error creating bridge: {e}")
            return False
        
        return False

    def detect_arp_conflicts(self) -> List[Tuple[str, str]]:
        """Detect potential ARP conflicts across network interfaces"""
        conflicts = []
        
        # Get all MAC addresses across interfaces
        interface_macs = {}
        
        try:
            for interface in netifaces.interfaces():
                if self._is_physical_interface(interface):
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_LINK in addrs:
                        mac = addrs[netifaces.AF_LINK][0].get('addr')
                        if mac:
                            if netifaces.AF_INET in addrs:
                                for addr in addrs[netifaces.AF_INET]:
                                    ip = addr.get('addr')
                                    if ip and not ip.startswith('127.'):
                                        if mac in interface_macs and interface_macs[mac] != ip:
                                            conflicts.append((ip, interface_macs[mac]))
                                        interface_macs[mac] = ip
        except Exception as e:
            print(f"Error detecting ARP conflicts: {e}")
            
        return conflicts

    def _update_interfaces(self):
        """Refresh active interface list and organize into network segments"""
        new_interfaces = {}
        new_network_segments = {}
        
        try:
            for interface in netifaces.interfaces():
                if self._is_physical_interface(interface):
                    if ip := self._get_interface_ip(interface):
                        new_interfaces[interface] = ip
                        
                        # Get network prefix for each IP
                        try:
                            addrs = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
                            for addr in addrs:
                                if 'addr' in addr and 'netmask' in addr and addr['addr'] == ip:
                                    # Calculate network prefix
                                    ip_obj = ipaddress.IPv4Address(ip)
                                    netmask = ipaddress.IPv4Address(addr['netmask'])
                                    network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                                    network_prefix = str(network.network_address)
                                    
                                    if network_prefix not in new_network_segments:
                                        new_network_segments[network_prefix] = []
                                    
                                    new_network_segments[network_prefix].append(ip)
                        except Exception as e:
                            print(f"Error calculating network prefix: {e}")
        
            # Update ARP table for cross-subnet communication
            self._update_arp_table()
            
        except Exception as e:
            print(f"Error updating interfaces: {e}")
        
        if new_interfaces != self.active_interfaces or new_network_segments != self.network_segments:
            self.active_interfaces = new_interfaces
            self.network_segments = new_network_segments
            
            # Check for potential conflicts
            conflicts = self.detect_arp_conflicts()
            if conflicts:
                print(f"Warning: Detected potential ARP conflicts: {conflicts}")
            
            # If we have multiple network segments, check if we should create a bridge
            if len(new_network_segments) > 1 and not self.bridges:
                # Find two interfaces to bridge
                interfaces = list(new_interfaces.keys())
                if len(interfaces) >= 2:
                    print(f"Multiple network segments detected. Creating virtual bridge between {interfaces[0]} and {interfaces[1]}")
                    self.create_virtual_bridge(interfaces[0], interfaces[1])
            
            for callback in self.listeners:
                try:
                    callback(self.active_interfaces)
                except Exception as e:
                    print(f"Error in interface change callback: {e}")

    def _update_arp_table(self):
        """Update ARP table for cross-subnet communication"""
        if self.platform == "Linux":
            try:
                # Read ARP table from system
                result = subprocess.run(['arp', '-n'], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')
                
                # Skip header
                for line in lines[1:]:
                    parts = line.split()
                    if len(parts) >= 3:
                        ip = parts[0]
                        mac = parts[2]
                        
                        # Determine network segment
                        for network, ips in self.network_segments.items():
                            try:
                                if ipaddress.IPv4Address(ip) in ipaddress.IPv4Network(network):
                                    if network not in self.arp_table:
                                        self.arp_table[network] = {}
                                    self.arp_table[network][ip] = mac
                            except:
                                pass
            except Exception as e:
                print(f"Error updating ARP table: {e}")
        elif self.platform == "Darwin":  # macOS
            try:
                result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 4:
                        hostname = parts[0]
                        ip = parts[1].strip('()')
                        mac = parts[3]
                        
                        # Determine network segment
                        for network, ips in self.network_segments.items():
                            try:
                                if ipaddress.IPv4Address(ip) in ipaddress.IPv4Network(network):
                                    if network not in self.arp_table:
                                        self.arp_table[network] = {}
                                    self.arp_table[network][ip] = mac
                            except:
                                pass
            except Exception as e:
                print(f"Error updating ARP table: {e}")
        elif self.platform == "Windows":
            try:
                result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
                lines = result.stdout.strip().split('\n')
                
                current_interface = None
                for line in lines:
                    if "Interface" in line:
                        parts = line.split()
                        current_interface = parts[1]
                    elif line.strip() and not line.startswith("Internet"):
                        parts = line.split()
                        if len(parts) >= 2:
                            ip = parts[0]
                            mac = parts[1]
                            
                            # Determine network segment
                            for network, ips in self.network_segments.items():
                                try:
                                    if ipaddress.IPv4Address(ip) in ipaddress.IPv4Network(network):
                                        if network not in self.arp_table:
                                            self.arp_table[network] = {}
                                        self.arp_table[network][ip] = mac
                                except:
                                    pass
            except Exception as e:
                print(f"Error updating ARP table: {e}")

    def _is_physical_interface(self, interface: str) -> bool:
        """Identify physical network interfaces based on platform"""
        # Skip loopback and virtual interfaces across all platforms
        excluded_patterns = ['lo', 'loop', 'docker', 'veth', 'virbr', 'vbox', 'vmnet']
        
        # Don't exclude bridges as we might have created them
        if interface in self.bridges:
            return True
            
        if any(pattern in interface.lower() for pattern in excluded_patterns):
            return False
            
        if self.platform == "Windows":
            # Windows interface naming is different
            return True  # Further filtering is done via IP address
        elif self.platform == "Darwin":  # macOS
            # On macOS, physical interfaces usually start with en (Ethernet/WiFi)
            return interface.startswith(('en', 'bridge', 'awdl'))
        else:  # Linux
            # Linux physical interfaces usually start with en, eth, or wl
            return interface.startswith(('en', 'eth', 'wl', 'br'))

    def _get_interface_ip(self, interface: str) -> Optional[str]:
        """Get IPv4 address for specific interface (cross-platform)"""
        try:
            # First check for any IPv4 address (works on all platforms)
            addrs = netifaces.ifaddresses(interface).get(netifaces.AF_INET, [])
            for addr in addrs:
                if 'addr' in addr and not addr['addr'].startswith('127.'):
                    return addr['addr']
            
            # Platform-specific fallback for interfaces without assigned IPs
            if self.platform == "Linux":
                return self._linux_handle_interface(interface)
            elif self.platform == "Darwin":  # macOS
                return self._macos_handle_interface(interface)
            elif self.platform == "Windows":
                return self._windows_handle_interface(interface)
                    
        except (ValueError, KeyError, IOError, Exception) as e:
            print(f"Error getting IP for interface {interface}: {e}")
        return None
    
    def _linux_handle_interface(self, interface: str) -> Optional[str]:
        """Linux-specific interface handling"""
        try:
            # Check interface status using system calls
            with open(f'/sys/class/net/{interface}/operstate') as f:
                if 'up' in f.read().lower():
                    # Try to use link-local addressing as a fallback
                    return self._assign_link_local_ip(interface)
        except Exception:
            pass
        return None
        
    def _macos_handle_interface(self, interface: str) -> Optional[str]:
        """macOS-specific interface handling"""
        try:
            # Check if interface is up using ifconfig
            result = subprocess.run(['ifconfig', interface], capture_output=True, text=True)
            if 'status: active' in result.stdout.lower():
                # On macOS, we can't easily assign IPs, so we'll use self-assigned link-local if needed
                ip = f"169.254.{random.randint(1,254)}.{random.randint(1,254)}"
                return ip
        except Exception:
            pass
        return None
        
    def _windows_handle_interface(self, interface: str) -> Optional[str]:
        """Windows-specific interface handling"""
        # Windows typically auto-assigns link-local IPs when needed
        # Just return None as Windows will handle this automatically
        return None

    def _assign_link_local_ip(self, interface: str) -> Optional[str]:
        """Assign Bonjour-style link-local address (Linux only)"""
        if self.platform != "Linux":
            return None
            
        ip = f"169.254.{random.randint(1,254)}.{random.randint(1,254)}"
        try:
            # Try with sudo if available
            if os.geteuid() == 0:  # Running as root
                os.system(f"ip addr add {ip}/16 dev {interface} >/dev/null 2>&1")
                os.system(f"ip link set {interface} up >/dev/null 2>&1")
            else:
                # Try with sudo
                os.system(f"sudo ip addr add {ip}/16 dev {interface} >/dev/null 2>&1")
                os.system(f"sudo ip link set {interface} up >/dev/null 2>&1")
            return ip
        except Exception as e:
            print(f"Error assigning link-local IP: {e}")
            return None

    def _interface_monitor(self):
        """Monitor for network changes"""
        while self.running:
            try:
                self._update_interfaces()
            except Exception as e:
                print(f"Error in network monitoring: {e}")
            time.sleep(self.check_interval)
            
    def get_route_to_host(self, target_ip: str) -> Optional[str]:
        """Determine best route to reach a specific host"""
        # Check if target IP is in our network segments
        for network, ips in self.network_segments.items():
            try:
                if ipaddress.IPv4Address(target_ip) in ipaddress.IPv4Network(network):
                    # Target is in this network segment, use any IP from this segment
                    if ips:
                        return ips[0]
            except:
                pass
                
        # If we have a bridge, use its IP
        for interface in self.active_interfaces:
            if interface in self.bridges:
                return self.active_interfaces[interface]
                
        # Last resort: use primary IP
        return self.get_primary_ip()