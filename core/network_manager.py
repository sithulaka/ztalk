import socket
import threading
import time
import netifaces
import random
import os
import platform
import subprocess
import ipaddress
import logging
from typing import Callable, Optional, Dict, List, Set, Tuple

class NetworkManager:
    def __init__(self):
        self.logger = logging.getLogger('NetworkManager')
        self._last_interfaces = {}  # Track previous state
        self._active_interfaces: Dict[str, str] = {}
        self._interface_listeners = []
        self._running = False
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
        self.unified_network = {}  # Store all discovered devices
        self.last_scan = 0
        self.scan_interval = 30  # Seconds between network scans

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
        return len(self._active_interfaces) > 0

    def add_interface_change_listener(self, callback: Callable):
        """Add callback for interface changes"""
        self.listeners.append(callback)

    def get_all_active_ips(self) -> Set[str]:
        return set(self._active_interfaces.values())

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
            for interface, ip in self._active_interfaces.items():
                if interface.startswith(pattern):
                    return ip
                    
        return next(iter(self._active_interfaces.values()), None) if self._active_interfaces else None

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

    def _update_interfaces(self) -> None:
        new_interfaces = {}
        
        try:
            interfaces = netifaces.interfaces()
            
            for iface in interfaces:
                if iface.startswith('lo'):
                    continue
                    
                addrs = netifaces.ifaddresses(iface)
                
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr['addr']
                        if not ip.startswith('127.') and not ip.startswith('169.254'):
                            new_interfaces[iface] = ip
                            # Only log if interface is new or IP changed
                            if iface not in self._last_interfaces or self._last_interfaces[iface] != ip:
                                self.logger.debug(f"Found active interface {iface} with IP {ip}")

            # Log only actual changes
            added = set(new_interfaces.keys()) - set(self._last_interfaces.keys())
            removed = set(self._last_interfaces.keys()) - set(new_interfaces.keys())
            
            if added or removed:
                if added:
                    self.logger.info(f"New interfaces detected: {added}")
                if removed:
                    self.logger.info(f"Interfaces removed: {removed}")

                # Notify listeners only if there are changes
                self._active_interfaces = new_interfaces
                for listener in self._interface_listeners:
                    listener(self._active_interfaces)
            
            self._last_interfaces = new_interfaces.copy()
                
        except Exception as e:
            self.logger.error(f"Error updating network interfaces: {e}")

    def _update_arp_table(self):
        """Update ARP table for cross-subnet communication"""
        if self.platform == "Linux":
            self._update_arp_table_linux()
        elif self.platform == "Darwin":
            self._update_arp_table_macos()
        elif self.platform == "Windows":
            self._update_arp_table_windows()

    def _update_arp_table_linux(self):
        try:
            result = subprocess.run(['arp', '-n'], capture_output=True, text=True)
            self._parse_arp_output(result.stdout)
        except Exception as e:
            self.logger.error(f"Error updating Linux ARP table: {e}")

    def _update_arp_table_macos(self):
        try:
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
            self._parse_arp_output(result.stdout)
        except Exception as e:
            self.logger.error(f"Error updating macOS ARP table: {e}")

    def _update_arp_table_windows(self):
        try:
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
            self._parse_arp_output(result.stdout)
        except Exception as e:
            self.logger.error(f"Error updating Windows ARP table: {e}")

    def _parse_arp_output(self, output: str):
        # Common parsing logic
        for line in output.strip().split('\n'):
            try:
                if self.platform == "Linux":
                    self._parse_linux_arp_line(line)
                elif self.platform == "Darwin":
                    self._parse_macos_arp_line(line)
                elif self.platform == "Windows":
                    self._parse_windows_arp_line(line)
            except Exception as e:
                self.logger.debug(f"Error parsing ARP line: {e}")

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

    def scan_network(self):
        """Scan all interfaces for devices"""
        current_time = time.time()
        if current_time - self.last_scan < self.scan_interval:
            return self.unified_network
            
        self.last_scan = current_time
        self.unified_network.clear()
        
        for interface, ip in self._active_interfaces.items():
            try:
                # Get network prefix
                ip_parts = ip.split('.')
                network_prefix = '.'.join(ip_parts[:-1])
                
                # Scan network range
                for i in range(1, 255):
                    target = f"{network_prefix}.{i}"
                    if target == ip:
                        continue
                        
                    # Fast ping scan
                    if self.platform == "Windows":
                        cmd = f"ping -n 1 -w 100 {target}"
                    else:
                        cmd = f"ping -c 1 -W 1 {target}"
                        
                    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    if result.returncode == 0:
                        # Device responded
                        try:
                            hostname = socket.gethostbyaddr(target)[0]
                        except:
                            hostname = "unknown"
                            
                        self.unified_network[target] = {
                            'hostname': hostname,
                            'interface': interface,
                            'type': 'WiFi' if interface.startswith(('wl', 'Wi-Fi')) else 'LAN'
                        }
                        
            except Exception as e:
                self.logger.error(f"Error scanning network on interface {interface}: {e}")
                
        return self.unified_network

    def get_unified_network(self):
        """Get all devices in the unified network view"""
        return self.scan_network()