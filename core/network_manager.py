"""
Network Manager Module for ZTalk

This module handles network interface discovery and management.
"""

import sys
import os
import time
import threading
import socket
import logging
import platform
import ipaddress
from typing import Dict, List, Tuple, Callable, Optional, Set, Any

# Import the netifaces compatibility module instead of netifaces directly
try:
    # First try to import from our compatibility module
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from netifaces_compat import interfaces, ifaddresses, gateways, AF_INET, AF_INET6, AF_LINK, is_fallback
    if is_fallback():
        logging.info("Using fallback netifaces implementation")
    else:
        logging.info("Using real netifaces implementation")
except ImportError:
    # If that fails, try to import netifaces directly
    try:
        import netifaces
        interfaces = netifaces.interfaces
        ifaddresses = netifaces.ifaddresses
        gateways = netifaces.gateways
        AF_INET = netifaces.AF_INET
        AF_INET6 = netifaces.AF_INET6
        AF_LINK = netifaces.AF_LINK
        logging.info("Using direct netifaces import")
    except ImportError:
        logging.error("Failed to import netifaces or netifaces_compat")
        raise

class NetworkManager:
    """
    Manages network interfaces and connections for local network communication.
    Provides automatic interface detection and IP configuration tools.
    """
    
    def __init__(self):
        # Network interface tracking
        self.active_interfaces: Dict[str, str] = {}  # {interface_name: ip}
        self.network_segments: Dict[str, List[str]] = {}  # {network_prefix: [ips]}
        
        # Interface change event listeners
        self.listeners: List[Callable] = []
        
        # Network monitoring thread
        self.running = True
        self._monitor_thread = threading.Thread(target=self._interface_monitor, daemon=True)
        self.check_interval = 5  # seconds
        
        # Platform detection
        self.platform = platform.system()  # 'Windows', 'Darwin' (macOS), or 'Linux'
        
        # Hardware address tracking
        self.mac_addresses: Dict[str, str] = {}  # {interface: mac}
        
        # Virtual interfaces (bridges)
        self.bridges: Set[str] = set()
        
        # IP conflict tracking
        self.arp_table: Dict[str, Dict[str, str]] = {}  # {network: {ip: mac}}
        
        # Network diagnostics data
        self.latency_data: Dict[str, float] = {}  # {ip: latency_ms}
        
    def start(self):
        """Start monitoring network interfaces"""
        self._update_interfaces()
        self._monitor_thread.start()
        return True

    def stop(self):
        """Stop monitoring network interfaces"""
        self.running = False
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
        return True
        
    def add_interface_change_listener(self, callback: Callable):
        """Add callback to be notified when interfaces change"""
        self.listeners.append(callback)
        
    def remove_interface_change_listener(self, callback: Callable):
        """Remove interface change listener"""
        if callback in self.listeners:
            self.listeners.remove(callback)
            
    def get_all_active_ips(self) -> List[str]:
        """Get IPs from all active physical interfaces"""
        return list(self.active_interfaces.values())
    
    def get_network_segments(self) -> Dict[str, List[str]]:
        """Get available network segments"""
        return self.network_segments.copy()
    
    def get_primary_ip(self) -> Optional[str]:
        """Get preferred IP (Ethernet first, then WiFi)"""
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
                    
        # If no preferred interface found, return the first one
        return next(iter(self.active_interfaces.values()), None) if self.active_interfaces else None
    
    def get_interface_details(self, interface_name: str) -> Dict[str, Any]:
        """Get detailed information about a network interface"""
        details = {
            "name": interface_name,
            "ip": None,
            "netmask": None,
            "gateway": None,
            "mac": None,
            "is_up": False,
            "mtu": None,
            "type": self._get_interface_type(interface_name)
        }
        
        try:
            # Get IP and netmask
            addrs = ifaddresses(interface_name)
            if AF_INET in addrs:
                for addr in addrs[AF_INET]:
                    if 'addr' in addr and not addr['addr'].startswith('127.'):
                        details["ip"] = addr.get('addr')
                        details["netmask"] = addr.get('netmask')
            
            # Get MAC address
            if AF_LINK in addrs:
                for addr in addrs[AF_LINK]:
                    if 'addr' in addr:
                        details["mac"] = addr.get('addr')
            
            # Get gateway if this is the default route
            gateways_info = gateways()
            if 'default' in gateways_info and AF_INET in gateways_info['default']:
                gw_addr, gw_iface = gateways_info['default'][AF_INET]
                if gw_iface == interface_name:
                    details["gateway"] = gw_addr
            
            # Get interface status on Linux/macOS
            if self.platform != "Windows":
                try:
                    if self.platform == "Linux":
                        output = subprocess.check_output(['ip', 'link', 'show', interface_name], 
                                                        stderr=subprocess.DEVNULL, 
                                                        universal_newlines=True)
                        details["is_up"] = "state UP" in output
                        
                        # Get MTU
                        for line in output.splitlines():
                            if "mtu" in line:
                                mtu_parts = line.split("mtu ")
                                if len(mtu_parts) > 1:
                                    details["mtu"] = int(mtu_parts[1].split()[0])
                                    
                    elif self.platform == "Darwin":  # macOS
                        output = subprocess.check_output(['ifconfig', interface_name], 
                                                        stderr=subprocess.DEVNULL, 
                                                        universal_newlines=True)
                        details["is_up"] = "status: active" in output
                        
                        # Get MTU
                        for line in output.splitlines():
                            if "mtu" in line:
                                parts = line.split()
                                for i, part in enumerate(parts):
                                    if part == "mtu" and i < len(parts) - 1:
                                        details["mtu"] = int(parts[i+1])
                except Exception:
                    pass
            else:
                # On Windows, assume the interface is up if it has an IP
                details["is_up"] = details["ip"] is not None
                
        except Exception as e:
            print(f"Error getting interface details for {interface_name}: {e}")
            
        return details
    
    def set_interface_ip(self, interface: str, ip: str, netmask: str, gateway: Optional[str] = None) -> bool:
        """Set IP configuration for an interface"""
        try:
            if self.platform == "Windows":
                # Windows netsh command
                cmd = f'netsh interface ip set address name="{interface}" static {ip} {netmask}'
                if gateway:
                    cmd += f" {gateway}"
                result = subprocess.run(cmd, shell=True, check=True, 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
            elif self.platform == "Linux":
                # Linux ip command
                # First flush existing IPs
                subprocess.run(['ip', 'addr', 'flush', 'dev', interface], 
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Calculate CIDR from netmask
                netmask_bits = sum(bin(int(x)).count('1') for x in netmask.split('.'))
                
                # Set new IP
                subprocess.run(['ip', 'addr', 'add', f"{ip}/{netmask_bits}", 'dev', interface], 
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Set interface up
                subprocess.run(['ip', 'link', 'set', interface, 'up'], 
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Set gateway if provided
                if gateway:
                    # Delete default route first
                    try:
                        subprocess.run(['ip', 'route', 'del', 'default'], 
                                      check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    except Exception:
                        pass  # Ignore if no default route exists
                    
                    # Add new default route
                    subprocess.run(['ip', 'route', 'add', 'default', 'via', gateway, 'dev', interface], 
                                  check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
            elif self.platform == "Darwin":  # macOS
                # macOS ifconfig command
                subprocess.run(['ifconfig', interface, 'inet', ip, 'netmask', netmask], 
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # Set gateway if provided
                if gateway:
                    # Delete default route first
                    try:
                        subprocess.run(['route', 'delete', 'default'], 
                                      check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    except Exception:
                        pass  # Ignore if no default route exists
                    
                    # Add new default route
                    subprocess.run(['route', 'add', 'default', gateway], 
                                  check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Update our interface list after changing IP
            self._update_interfaces()
            return True
            
        except Exception as e:
            print(f"Error setting IP configuration: {e}")
            return False
    
    def detect_ip_conflict(self, ip: str) -> Optional[str]:
        """
        Check if an IP address is already in use on the network.
        Returns the MAC address of the conflicting host, or None if no conflict.
        """
        try:
            # Find the network segment this IP belongs to
            ip_obj = ipaddress.IPv4Address(ip)
            for network_str, ips in self.network_segments.items():
                network = ipaddress.IPv4Network(network_str)
                if ip_obj in network:
                    # Check if IP is in our ARP table
                    if network_str in self.arp_table and ip in self.arp_table[network_str]:
                        return self.arp_table[network_str][ip]
                    
                    # Try to ping to update ARP table
                    self._ping_host(ip)
                    self._update_arp_table()
                    
                    # Check again
                    if network_str in self.arp_table and ip in self.arp_table[network_str]:
                        return self.arp_table[network_str][ip]
            
            return None
        except Exception as e:
            print(f"Error detecting IP conflict: {e}")
            return None
    
    def ping_scan_network(self, network_prefix: Optional[str] = None) -> Dict[str, float]:
        """
        Scan a network segment by pinging all possible hosts.
        Returns a dictionary of responding IPs and their latencies.
        """
        results = {}
        
        # Determine which network to scan
        networks_to_scan = []
        if network_prefix:
            try:
                networks_to_scan.append(ipaddress.IPv4Network(network_prefix))
            except ValueError:
                print(f"Invalid network prefix: {network_prefix}")
                return results
        else:
            # Scan all network segments
            for network_str in self.network_segments:
                try:
                    networks_to_scan.append(ipaddress.IPv4Network(network_str))
                except ValueError:
                    continue
        
        # Limit scan to smaller networks
        active_hosts = []
        for network in networks_to_scan:
            # Only scan small networks (< 256 hosts) to avoid taking too long
            if network.num_addresses <= 256:
                for host in network.hosts():
                    host_ip = str(host)
                    # Skip our own IPs
                    if host_ip in self.active_interfaces.values():
                        continue
                    active_hosts.append(host_ip)
        
        # Ping each host in a thread pool
        max_threads = 15  # Limit concurrent pings
        threads = []
        results_lock = threading.Lock()
        
        def ping_worker(ip):
            latency = self._ping_host(ip)
            if latency is not None:
                with results_lock:
                    results[ip] = latency
        
        # Start ping threads
        for ip in active_hosts:
            if len(threads) >= max_threads:
                # Wait for a thread to finish before starting a new one
                for t in list(threads):
                    if not t.is_alive():
                        threads.remove(t)
                if len(threads) >= max_threads:
                    time.sleep(0.1)
            
            # Start a new thread
            thread = threading.Thread(target=ping_worker, args=(ip,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to finish
        for thread in threads:
            thread.join(timeout=1.0)
        
        # Update latency data
        self.latency_data.update(results)
        
        return results
    
    def _interface_monitor(self):
        """Thread function that monitors network interfaces"""
        while self.running:
            try:
                self._update_interfaces()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in interface monitor: {e}")
                # Don't crash the thread on error
                time.sleep(self.check_interval)
    
    def _update_interfaces(self):
        """Update the list of active interfaces and their IPs"""
        new_interfaces = {}
        new_network_segments = {}
        
        try:
            for interface in interfaces():
                if self._is_physical_interface(interface):
                    ip = self._get_interface_ip(interface)
                    if ip:
                        new_interfaces[interface] = ip
                        
                        # Get MAC address if available
                        addrs = ifaddresses(interface)
                        if AF_LINK in addrs and addrs[AF_LINK]:
                            mac = addrs[AF_LINK][0].get('addr')
                            if mac:
                                self.mac_addresses[interface] = mac
                        
                        # Calculate network segments
                        try:
                            if AF_INET in addrs:
                                for addr in addrs[AF_INET]:
                                    if 'addr' in addr and 'netmask' in addr and addr['addr'] == ip:
                                        # Convert to network prefix
                                        ip_obj = ipaddress.IPv4Address(ip)
                                        netmask = ipaddress.IPv4Address(addr['netmask'])
                                        network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
                                        network_prefix = str(network.network_address) + "/" + str(network.prefixlen)
                                        
                                        if network_prefix not in new_network_segments:
                                            new_network_segments[network_prefix] = []
                                        
                                        new_network_segments[network_prefix].append(ip)
                        except Exception as e:
                            print(f"Error calculating network prefix: {e}")
            
            # Update the ARP table for cross-subnet communication
            self._update_arp_table()
            
        except Exception as e:
            print(f"Error updating interfaces: {e}")
        
        # Check if interfaces have changed
        if new_interfaces != self.active_interfaces or new_network_segments != self.network_segments:
            old_interfaces = self.active_interfaces.copy()
            self.active_interfaces = new_interfaces
            self.network_segments = new_network_segments
            
            # Notify listeners of the change
            for callback in self.listeners:
                try:
                    callback(self.active_interfaces, old_interfaces)
                except Exception as e:
                    print(f"Error in interface change callback: {e}")
    
    def _is_physical_interface(self, interface: str) -> bool:
        """Determine if this is a physical (not virtual/loopback) interface"""
        # Skip loopback interfaces
        if interface == 'lo' or interface.startswith('loop'):
            return False
            
        # Skip Docker and other virtual interfaces
        if interface.startswith(('docker', 'veth', 'vnet', 'tun', 'tap', 'virbr')):
            return False
            
        # Platform specific checks
        if self.platform == "Windows":
            # Skip Hyper-V and other virtual adapters
            if any(substr in interface.lower() for substr in ('hyper-v', 'virtual', 'miniport')):
                return False
        elif self.platform == "Darwin":  # macOS
            # Skip VirtualBox and other virtual adapters
            if interface.startswith(('vboxnet', 'utun')):
                return False
        else:  # Linux
            # Check if this is a bridge we created
            if interface in self.bridges:
                return True
                
            # Skip other virtual interfaces
            if interface.startswith(('vmnet', 'vbox')):
                return False
        
        return True
    
    def _get_interface_ip(self, interface: str) -> Optional[str]:
        """Get the IP address for an interface"""
        try:
            addrs = ifaddresses(interface)
            if AF_INET in addrs:
                for addr in addrs[AF_INET]:
                    if 'addr' in addr and not addr['addr'].startswith('127.'):
                        return addr['addr']
        except Exception as e:
            print(f"Error getting IP for interface {interface}: {e}")
        
        return None
        
    def _get_interface_type(self, interface: str) -> str:
        """Determine the type of network interface (Ethernet, WiFi, etc.)"""
        if self.platform == "Windows":
            if "wi-fi" in interface.lower() or "wireless" in interface.lower():
                return "WiFi"
            elif "ethernet" in interface.lower() or "local area connection" in interface.lower():
                return "Ethernet"
        elif self.platform == "Darwin":  # macOS
            if interface.startswith("en"):
                if interface == "en0":
                    return "WiFi"  # Typically en0 is WiFi on macOS laptops
                else:
                    return "Ethernet"
        else:  # Linux
            if interface.startswith("wl"):
                return "WiFi"
            elif interface.startswith(("eth", "en")):
                return "Ethernet"
            elif interface.startswith("br"):
                return "Bridge"
        
        return "Unknown"
    
    def _update_arp_table(self):
        """Update ARP table for IP-to-MAC mappings"""
        try:
            if self.platform == "Linux":
                # Read ARP table on Linux
                with open('/proc/net/arp', 'r') as f:
                    lines = f.readlines()[1:]  # Skip header
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 6:
                            ip, hw_type, flags, mac, mask, device = parts[:6]
                            
                            # Skip incomplete entries
                            if mac == '00:00:00:00:00:00':
                                continue
                                
                            # Find which network this IP belongs to
                            try:
                                ip_obj = ipaddress.IPv4Address(ip)
                                for network_str in self.network_segments:
                                    network = ipaddress.IPv4Network(network_str)
                                    if ip_obj in network:
                                        if network_str not in self.arp_table:
                                            self.arp_table[network_str] = {}
                                        self.arp_table[network_str][ip] = mac
                                        break
                            except Exception:
                                continue
            
            elif self.platform == "Darwin":  # macOS
                # Use arp command on macOS
                try:
                    output = subprocess.check_output(['arp', '-a'], universal_newlines=True)
                    for line in output.splitlines():
                        if '(' in line and ')' in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                ip = line.split('(')[1].split(')')[0]
                                mac = parts[3]
                                
                                # Find which network this IP belongs to
                                try:
                                    ip_obj = ipaddress.IPv4Address(ip)
                                    for network_str in self.network_segments:
                                        network = ipaddress.IPv4Network(network_str)
                                        if ip_obj in network:
                                            if network_str not in self.arp_table:
                                                self.arp_table[network_str] = {}
                                            self.arp_table[network_str][ip] = mac
                                            break
                                except Exception:
                                    continue
                except Exception:
                    pass
            
            elif self.platform == "Windows":
                # Use arp command on Windows
                try:
                    output = subprocess.check_output(['arp', '-a'], universal_newlines=True)
                    for line in output.splitlines():
                        parts = line.split()
                        if len(parts) >= 3 and parts[0][0].isdigit():
                            ip = parts[0]
                            mac = parts[1].replace('-', ':')
                            
                            # Find which network this IP belongs to
                            try:
                                ip_obj = ipaddress.IPv4Address(ip)
                                for network_str in self.network_segments:
                                    network = ipaddress.IPv4Network(network_str)
                                    if ip_obj in network:
                                        if network_str not in self.arp_table:
                                            self.arp_table[network_str] = {}
                                        self.arp_table[network_str][ip] = mac
                                        break
                            except Exception:
                                continue
                except Exception:
                    pass
        
        except Exception as e:
            print(f"Error updating ARP table: {e}")
    
    def _ping_host(self, ip: str) -> Optional[float]:
        """Ping a host and return latency in ms (or None if unreachable)"""
        try:
            if self.platform == "Windows":
                cmd = ['ping', '-n', '1', '-w', '1000', ip]
            else:  # Linux and macOS
                cmd = ['ping', '-c', '1', '-W', '1', ip]
                
            start_time = time.time()
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            end_time = time.time()
            
            if result.returncode == 0:
                return (end_time - start_time) * 1000  # Convert to ms
            return None
        except Exception:
            return None