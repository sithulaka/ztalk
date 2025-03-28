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
import subprocess
import json
import random
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
        
        # Fallback discovery
        self.discovery_methods = [
            self._primary_device_discovery,
            self._arp_device_discovery,
            self._icmp_device_discovery,
            self._mdns_device_discovery,
            self._netbios_device_discovery,
            self._common_ports_scan_discovery
        ]
        self.discovery_fallback_index = 0
        self.discovered_devices: Dict[str, Dict[str, Any]] = {}  # {ip: {details}}
        
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
    
    def discover_local_devices(self, force_fallback: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Discover devices on the local network using all available methods
        
        Args:
            force_fallback: If True, try all fallback methods instead of just primary discovery
            
        Returns:
            Dictionary of discovered devices with IP as key and device details as value
        """
        # Reset discovered devices if force_fallback
        if force_fallback:
            self.discovered_devices = {}
            
        # Get current network segment
        network_prefix = self._get_current_network_prefix()
        if not network_prefix:
            logging.warning("No active network interface found for device discovery")
            return {}
            
        # Try primary discovery first unless forcing fallback
        if not force_fallback:
            devices = self._primary_device_discovery(network_prefix)
            if devices:
                self.discovered_devices.update(devices)
                return self.discovered_devices
                
        # If primary failed or force_fallback, try fallback methods
        logging.info("Primary device discovery failed or skipped, using fallback methods")
        self._try_fallback_discovery_methods(network_prefix)
            
        return self.discovered_devices
    
    def _try_fallback_discovery_methods(self, network_prefix: str):
        """Try fallback discovery methods one by one"""
        # Skip the primary discovery method which is first in the list
        for method in self.discovery_methods[1:]:
            logging.info(f"Trying fallback discovery method: {method.__name__}")
            try:
                devices = method(network_prefix)
                if devices:
                    self.discovered_devices.update(devices)
                    # If we found devices, we can stop
                    if len(self.discovered_devices) > 0:
                        logging.info(f"Discovered {len(devices)} devices with {method.__name__}")
                        break
            except Exception as e:
                logging.warning(f"Fallback method {method.__name__} failed: {e}")
                continue
    
    def _get_current_network_prefix(self) -> Optional[str]:
        """Get the current network prefix (e.g., 192.168.1.)"""
        ip = self.get_primary_ip()
        if not ip:
            return None
            
        # Extract network prefix
        parts = ip.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}."
        return None
    
    def _primary_device_discovery(self, network_prefix: str) -> Dict[str, Dict[str, Any]]:
        """Primary device discovery method using a combination of ARP and ping scan"""
        devices = {}
        
        # Start with ARP table lookup
        self._update_arp_table()
        for network, ips in self.arp_table.items():
            if network.startswith(network_prefix):
                for ip, mac in ips.items():
                    devices[ip] = {
                        "ip": ip,
                        "mac": mac,
                        "hostname": self._resolve_hostname(ip),
                        "discovery_method": "arp",
                        "last_seen": time.time()
                    }
        
        # Supplement with ping scan
        ping_results = self.ping_scan_network(network_prefix)
        for ip, latency in ping_results.items():
            if ip not in devices:
                devices[ip] = {
                    "ip": ip,
                    "latency": latency,
                    "hostname": self._resolve_hostname(ip),
                    "discovery_method": "ping",
                    "last_seen": time.time()
                }
            else:
                devices[ip]["latency"] = latency
                devices[ip]["last_seen"] = time.time()
                
        return devices
    
    def _arp_device_discovery(self, network_prefix: str) -> Dict[str, Dict[str, Any]]:
        """Discover devices using ARP requests"""
        devices = {}
        
        # Force ARP table update with broadcast ping
        try:
            if self.platform == "Windows":
                subprocess.run(["ping", "-n", "1", "-w", "500", "-b", f"{network_prefix}255"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["ping", "-c", "1", "-W", "1", "-b", f"{network_prefix}255"], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
            
        # Run arp command and parse output
        try:
            if self.platform == "Windows":
                output = subprocess.check_output(["arp", "-a"], universal_newlines=True)
                for line in output.splitlines():
                    if network_prefix in line:
                        parts = [p for p in line.split() if p.strip()]
                        if len(parts) >= 2:
                            ip = parts[0]
                            if ip.startswith(network_prefix):
                                mac = parts[1].replace('-', ':')
                                devices[ip] = {
                                    "ip": ip,
                                    "mac": mac,
                                    "hostname": self._resolve_hostname(ip),
                                    "discovery_method": "arp-command",
                                    "last_seen": time.time()
                                }
            else:
                output = subprocess.check_output(["arp", "-n"], universal_newlines=True)
                for line in output.splitlines():
                    if network_prefix in line and "(" not in line and "incomplete" not in line:
                        parts = [p for p in line.split() if p.strip()]
                        if len(parts) >= 3:
                            ip = parts[0]
                            mac = parts[2]
                            devices[ip] = {
                                "ip": ip,
                                "mac": mac,
                                "hostname": self._resolve_hostname(ip),
                                "discovery_method": "arp-command",
                                "last_seen": time.time()
                            }
        except Exception as e:
            logging.warning(f"ARP command failed: {e}")
            
        return devices
    
    def _icmp_device_discovery(self, network_prefix: str) -> Dict[str, Dict[str, Any]]:
        """Discover devices using ICMP ping sweep"""
        devices = {}
        
        # Get subnet size from first interface in this network
        subnet_size = 24  # Default to /24
        for interface in self.active_interfaces:
            details = self.get_interface_details(interface)
            if details['ip'] and details['ip'].startswith(network_prefix):
                if details['netmask']:
                    # Convert netmask to CIDR
                    try:
                        subnet_size = sum(bin(int(x)).count('1') for x in details['netmask'].split('.'))
                    except Exception:
                        pass
                break
        
        # Calculate range of IPs to scan based on subnet
        ip_range = []
        if subnet_size == 24:
            # Standard /24 network, scan all 254 addresses
            for i in range(1, 255):
                ip_range.append(f"{network_prefix}{i}")
        elif subnet_size < 24:
            # Larger network, just scan a sample
            for octet3 in range(0, 256):
                for octet4 in random.sample(range(1, 255), 3):  # Just 3 random IPs per subnet
                    ip_range.append(f"{network_prefix[:network_prefix.rindex('.')]}.{octet3}.{octet4}")
        else:
            # Smaller subnet, scan everything
            base = network_prefix[:network_prefix.rindex('.')]
            last_octet = int(network_prefix[network_prefix.rindex('.')+1:])
            host_bits = 32 - subnet_size
            hosts = 2 ** host_bits - 2  # Subtract network and broadcast addresses
            for i in range(1, hosts + 1):
                ip = f"{base}.{last_octet + i}"
                ip_range.append(ip)
        
        # Use multiple threads for faster scanning
        max_threads = 10
        threads = []
        results = {}
        
        def ping_worker(ip_list):
            for ip in ip_list:
                latency = self._ping_host(ip)
                if latency is not None:
                    results[ip] = latency
        
        # Split work among threads
        chunk_size = max(1, len(ip_range) // max_threads)
        for i in range(0, len(ip_range), chunk_size):
            chunk = ip_range[i:i+chunk_size]
            thread = threading.Thread(target=ping_worker, args=(chunk,))
            thread.daemon = True
            threads.append(thread)
            thread.start()
            
        # Wait for all threads to complete (with timeout)
        for thread in threads:
            thread.join(timeout=5.0)
            
        # Process results
        for ip, latency in results.items():
            devices[ip] = {
                "ip": ip,
                "latency": latency,
                "hostname": self._resolve_hostname(ip),
                "discovery_method": "icmp",
                "last_seen": time.time()
            }
            
        return devices
    
    def _mdns_device_discovery(self, network_prefix: str) -> Dict[str, Dict[str, Any]]:
        """Discover devices using mDNS (multicast DNS)"""
        devices = {}
        
        # Check if we have zeroconf module available
        try:
            from zeroconf import Zeroconf, ServiceBrowser
            
            class MDNSListener:
                def __init__(self):
                    self.devices = {}
                    
                def add_service(self, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info:
                        addresses = info.parsed_addresses()
                        for addr in addresses:
                            if addr.startswith(network_prefix):
                                self.devices[addr] = {
                                    "ip": addr,
                                    "hostname": name,
                                    "service": type_,
                                    "port": info.port,
                                    "discovery_method": "mdns",
                                    "last_seen": time.time()
                                }
                
                def remove_service(self, zc, type_, name):
                    pass
                    
                def update_service(self, zc, type_, name):
                    self.add_service(zc, type_, name)
            
            # Create zeroconf and browser instances
            zeroconf = Zeroconf()
            listener = MDNSListener()
            
            # Browse for common service types
            browsers = []
            service_types = [
                "_http._tcp.local.",
                "_https._tcp.local.",
                "_ssh._tcp.local.",
                "_workstation._tcp.local.",
                "_device-info._tcp.local.",
                "_googlecast._tcp.local.",
                "_spotify-connect._tcp.local.",
                "_printer._tcp.local.",
                "_ipp._tcp.local.",
                "_smb._tcp.local.",
                "_afpovertcp._tcp.local."
            ]
            
            for service_type in service_types:
                browsers.append(ServiceBrowser(zeroconf, service_type, listener))
            
            # Give some time for discovery
            time.sleep(3.0)
            
            # Cleanup
            for browser in browsers:
                browser.cancel()
            zeroconf.close()
            
            # Return discovered devices
            devices = listener.devices
            
        except ImportError:
            logging.warning("zeroconf module not available for mDNS discovery")
            
        return devices
    
    def _netbios_device_discovery(self, network_prefix: str) -> Dict[str, Dict[str, Any]]:
        """Discover devices using NetBIOS name service"""
        devices = {}
        
        # NetBIOS is mainly on Windows systems
        if self.platform != "Windows":
            return devices
            
        try:
            # Use nbtscan or net view command on Windows
            if self.platform == "Windows":
                output = subprocess.check_output(["net", "view"], universal_newlines=True)
                for line in output.splitlines():
                    if "\\" in line:
                        hostname = line.split("\\")[1].strip()
                        try:
                            # Try to resolve the hostname to an IP
                            ip = socket.gethostbyname(hostname)
                            if ip.startswith(network_prefix):
                                devices[ip] = {
                                    "ip": ip,
                                    "hostname": hostname,
                                    "discovery_method": "netbios",
                                    "last_seen": time.time()
                                }
                        except Exception:
                            pass
            else:
                # Try nbtscan command on Linux/macOS if available
                try:
                    output = subprocess.check_output(["nbtscan", network_prefix + "0/24"], 
                                                    universal_newlines=True)
                    for line in output.splitlines():
                        parts = line.split()
                        if len(parts) >= 2 and parts[0].startswith(network_prefix):
                            ip = parts[0]
                            hostname = parts[1]
                            devices[ip] = {
                                "ip": ip,
                                "hostname": hostname,
                                "discovery_method": "netbios",
                                "last_seen": time.time()
                            }
                except Exception:
                    pass
        except Exception as e:
            logging.warning(f"NetBIOS discovery failed: {e}")
            
        return devices
    
    def _common_ports_scan_discovery(self, network_prefix: str) -> Dict[str, Dict[str, Any]]:
        """Discover devices by scanning common ports on the network"""
        devices = {}
        
        # Common ports to scan
        common_ports = [80, 443, 22, 21, 25, 3389, 5900, 8080, 8443]
        
        # Define a small set of IPs to scan (we don't want to scan all 254 IPs for all ports)
        ips_to_scan = []
        
        # Include DHCP range (usually .100 to .200)
        for i in range(100, 201):
            ips_to_scan.append(f"{network_prefix}{i}")
            
        # Include common device IPs
        common_ips = [1, 2, 10, 20, 50, 51, 100, 101, 254, 253]
        for i in common_ips:
            ip = f"{network_prefix}{i}"
            if ip not in ips_to_scan:
                ips_to_scan.append(ip)
                
        # Maximum targets to prevent excessive scanning
        max_targets = 25
        if len(ips_to_scan) > max_targets:
            ips_to_scan = random.sample(ips_to_scan, max_targets)
            
        # Scan for each port across all IPs
        for port in common_ports:
            for ip in ips_to_scan:
                if ip in devices:
                    continue  # Skip IPs we've already found
                    
                try:
                    # Simple socket connect with short timeout
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(0.5)
                    result = s.connect_ex((ip, port))
                    s.close()
                    
                    if result == 0:  # Port is open
                        devices[ip] = {
                            "ip": ip,
                            "open_port": port,
                            "hostname": self._resolve_hostname(ip),
                            "discovery_method": "port-scan",
                            "last_seen": time.time()
                        }
                except Exception:
                    pass
                    
        return devices
    
    def _resolve_hostname(self, ip: str) -> Optional[str]:
        """Resolve IP address to hostname"""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except (socket.herror, socket.gaierror):
            return None
            
    def get_unified_network(self) -> Dict[str, Dict[str, Any]]:
        """Get a unified view of the network combining all discovery methods"""
        # Force discovery with all methods
        self.discover_local_devices(force_fallback=True)
        return self.discovered_devices