#!/usr/bin/env python3
"""
Netifaces compatibility module for ZTalk

This module provides compatibility for the netifaces module, which can be
difficult to install in some environments due to compilation requirements.

It attempts to import the original netifaces module, and if that fails,
it provides minimal fallback functionality for basic netifaces operations.
"""

import sys
import socket
import subprocess
import re
import os
import logging
from typing import Dict, List, Union, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('netifaces_compat')

# Try to import the real netifaces module
try:
    import netifaces as real_netifaces
    logger.info("Using real netifaces module")
    
    # Re-export all from the real module
    AF_INET = real_netifaces.AF_INET
    AF_INET6 = real_netifaces.AF_INET6
    AF_LINK = real_netifaces.AF_LINK
    
    interfaces = real_netifaces.interfaces
    ifaddresses = real_netifaces.ifaddresses
    gateways = real_netifaces.gateways
    
except ImportError:
    logger.warning("Could not import netifaces, using fallback implementation")
    
    # Define constants that match the real netifaces module
    AF_INET = socket.AF_INET
    AF_INET6 = socket.AF_INET6
    AF_LINK = 17  # This is typically the value on most systems
    
    def interfaces() -> List[str]:
        """
        Get a list of network interface names.
        
        Returns:
            List of interface names
        """
        if sys.platform.startswith('linux'):
            return _linux_interfaces()
        elif sys.platform.startswith('darwin'):
            return _macos_interfaces()
        elif sys.platform.startswith('win'):
            return _windows_interfaces()
        else:
            logger.warning(f"Unsupported platform: {sys.platform}")
            return []
    
    def ifaddresses(interface: str) -> Dict[int, List[Dict[str, str]]]:
        """
        Get the addresses for a network interface.
        
        Args:
            interface: Name of the interface
            
        Returns:
            Dictionary of address family -> list of address info dictionaries
        """
        if sys.platform.startswith('linux'):
            return _linux_ifaddresses(interface)
        elif sys.platform.startswith('darwin'):
            return _macos_ifaddresses(interface)
        elif sys.platform.startswith('win'):
            return _windows_ifaddresses(interface)
        else:
            logger.warning(f"Unsupported platform: {sys.platform}")
            return {}
    
    def gateways() -> Dict[str, Any]:
        """
        Get the network gateway addresses.
        
        Returns:
            Dictionary of gateway information
        """
        if sys.platform.startswith('linux'):
            return _linux_gateways()
        elif sys.platform.startswith('darwin'):
            return _macos_gateways()
        elif sys.platform.startswith('win'):
            return _windows_gateways()
        else:
            logger.warning(f"Unsupported platform: {sys.platform}")
            return {'default': {}}
    
    # Linux implementations
    def _linux_interfaces() -> List[str]:
        try:
            # Use ip command if available
            if os.path.exists('/sbin/ip') or os.system('which ip >/dev/null 2>&1') == 0:
                output = subprocess.check_output(['ip', 'link', 'show'], 
                                              universal_newlines=True)
                interfaces = []
                for line in output.splitlines():
                    if ': ' in line:
                        iface = line.split(': ')[1].split(':')[0]
                        interfaces.append(iface)
                return interfaces
            else:
                # Fallback to reading /sys/class/net
                return os.listdir('/sys/class/net')
        except Exception as e:
            logger.error(f"Error getting interfaces: {e}")
            return []
    
    def _linux_ifaddresses(interface: str) -> Dict[int, List[Dict[str, str]]]:
        result = {}
        try:
            # Get IPv4 addresses
            output = subprocess.check_output(
                ['ip', 'addr', 'show', interface], 
                universal_newlines=True
            )
            
            # Parse IPv4 addresses
            ipv4_addresses = []
            for line in output.splitlines():
                line = line.strip()
                if 'inet ' in line:
                    parts = line.split()
                    addr, prefix = parts[1].split('/')
                    for i, part in enumerate(parts):
                        if part == 'brd':
                            broadcast = parts[i+1]
                            break
                    else:
                        broadcast = ''
                    
                    ipv4_addresses.append({
                        'addr': addr,
                        'netmask': _prefix_to_netmask(int(prefix)),
                        'broadcast': broadcast
                    })
            
            if ipv4_addresses:
                result[AF_INET] = ipv4_addresses
                
            # Parse IPv6 addresses
            ipv6_addresses = []
            for line in output.splitlines():
                line = line.strip()
                if 'inet6 ' in line:
                    parts = line.split()
                    addr, prefix = parts[1].split('/')
                    ipv6_addresses.append({
                        'addr': addr,
                        'netmask': prefix,
                        'scope': parts[3] if len(parts) > 3 else '0'
                    })
            
            if ipv6_addresses:
                result[AF_INET6] = ipv6_addresses
                
            # Parse MAC address
            mac_addresses = []
            for line in output.splitlines():
                line = line.strip()
                if 'link/ether ' in line:
                    parts = line.split()
                    mac = parts[1]
                    mac_addresses.append({
                        'addr': mac,
                        'broadcast': 'ff:ff:ff:ff:ff:ff'
                    })
            
            if mac_addresses:
                result[AF_LINK] = mac_addresses
                
        except Exception as e:
            logger.error(f"Error getting addresses for {interface}: {e}")
        
        return result
    
    def _linux_gateways() -> Dict[str, Any]:
        result = {'default': {}}
        try:
            output = subprocess.check_output(['ip', 'route'], universal_newlines=True)
            
            for line in output.splitlines():
                parts = line.split()
                if 'default' in parts:
                    gw_index = parts.index('via') + 1 if 'via' in parts else -1
                    dev_index = parts.index('dev') + 1 if 'dev' in parts else -1
                    
                    if gw_index != -1 and dev_index != -1:
                        gw = parts[gw_index]
                        dev = parts[dev_index]
                        
                        # Find the interface index
                        iface_index = -1
                        for i, iface in enumerate(interfaces()):
                            if iface == dev:
                                iface_index = i
                                break
                        
                        result['default'][AF_INET] = (gw, dev, iface_index)
        
        except Exception as e:
            logger.error(f"Error getting gateways: {e}")
        
        return result
    
    # macOS implementations
    def _macos_interfaces() -> List[str]:
        try:
            output = subprocess.check_output(['ifconfig'], universal_newlines=True)
            interfaces = []
            
            for line in output.splitlines():
                if ': ' in line:
                    iface = line.split(': ')[0]
                    interfaces.append(iface)
            
            return interfaces
        except Exception as e:
            logger.error(f"Error getting interfaces: {e}")
            return []
    
    def _macos_ifaddresses(interface: str) -> Dict[int, List[Dict[str, str]]]:
        result = {}
        try:
            output = subprocess.check_output(
                ['ifconfig', interface], 
                universal_newlines=True
            )
            
            # Parse IPv4 addresses
            ipv4_pattern = r'inet\s+(\d+\.\d+\.\d+\.\d+)\s+netmask\s+0x([0-9a-f]{8})(?:\s+broadcast\s+(\d+\.\d+\.\d+\.\d+))?'
            ipv4_matches = re.findall(ipv4_pattern, output)
            
            if ipv4_matches:
                ipv4_addresses = []
                for addr, netmask_hex, broadcast in ipv4_matches:
                    netmask = _hex_to_dotted_quad(netmask_hex)
                    ipv4_addresses.append({
                        'addr': addr,
                        'netmask': netmask,
                        'broadcast': broadcast if broadcast else ''
                    })
                result[AF_INET] = ipv4_addresses
            
            # Parse IPv6 addresses
            ipv6_pattern = r'inet6\s+([0-9a-f:]+)(?:%\w+)?\s+prefixlen\s+(\d+)'
            ipv6_matches = re.findall(ipv6_pattern, output)
            
            if ipv6_matches:
                ipv6_addresses = []
                for addr, prefixlen in ipv6_matches:
                    ipv6_addresses.append({
                        'addr': addr,
                        'netmask': prefixlen,
                        'scope': '0'
                    })
                result[AF_INET6] = ipv6_addresses
            
            # Parse MAC address
            mac_pattern = r'ether\s+([0-9a-f:]+)'
            mac_match = re.search(mac_pattern, output)
            
            if mac_match:
                mac = mac_match.group(1)
                result[AF_LINK] = [{
                    'addr': mac,
                    'broadcast': 'ff:ff:ff:ff:ff:ff'
                }]
        
        except Exception as e:
            logger.error(f"Error getting addresses for {interface}: {e}")
        
        return result
    
    def _macos_gateways() -> Dict[str, Any]:
        result = {'default': {}}
        try:
            output = subprocess.check_output(['netstat', '-nr'], universal_newlines=True)
            
            for line in output.splitlines():
                if line.startswith('default'):
                    parts = line.split()
                    if len(parts) >= 2:
                        gw = parts[1]
                        dev = parts[len(parts) - 1] if len(parts) > 3 else ''
                        
                        # Find the interface index
                        iface_index = -1
                        for i, iface in enumerate(interfaces()):
                            if iface == dev:
                                iface_index = i
                                break
                        
                        result['default'][AF_INET] = (gw, dev, iface_index)
        
        except Exception as e:
            logger.error(f"Error getting gateways: {e}")
        
        return result
    
    # Windows implementations
    def _windows_interfaces() -> List[str]:
        try:
            output = subprocess.check_output(['ipconfig', '/all'], universal_newlines=True)
            interfaces = []
            
            adapter_pattern = r'Ethernet adapter (.*?):'
            wireless_pattern = r'Wireless LAN adapter (.*?):'
            
            for match in re.finditer(adapter_pattern, output):
                interfaces.append(match.group(1).strip())
            
            for match in re.finditer(wireless_pattern, output):
                interfaces.append(match.group(1).strip())
            
            return interfaces
        except Exception as e:
            logger.error(f"Error getting interfaces: {e}")
            return []
    
    def _windows_ifaddresses(interface: str) -> Dict[int, List[Dict[str, str]]]:
        result = {}
        try:
            output = subprocess.check_output(
                ['ipconfig', '/all'], 
                universal_newlines=True
            )
            
            # Find the section for this interface
            sections = re.split(r'(?:Ethernet|Wireless LAN) adapter ', output)[1:]
            interface_section = None
            
            for section in sections:
                if section.startswith(interface):
                    interface_section = section
                    break
            
            if not interface_section:
                return result
            
            # Parse IPv4 addresses
            ipv4_pattern = r'IPv4 Address[^:]*:\s+(\d+\.\d+\.\d+\.\d+)'
            ipv4_mask_pattern = r'Subnet Mask[^:]*:\s+(\d+\.\d+\.\d+\.\d+)'
            
            ipv4_match = re.search(ipv4_pattern, interface_section)
            mask_match = re.search(ipv4_mask_pattern, interface_section)
            
            if ipv4_match and mask_match:
                addr = ipv4_match.group(1)
                netmask = mask_match.group(1)
                
                result[AF_INET] = [{
                    'addr': addr,
                    'netmask': netmask,
                    'broadcast': ''
                }]
            
            # Parse IPv6 addresses
            ipv6_pattern = r'IPv6 Address[^:]*:\s+([0-9a-f:]+)'
            ipv6_match = re.search(ipv6_pattern, interface_section)
            
            if ipv6_match:
                addr = ipv6_match.group(1)
                
                result[AF_INET6] = [{
                    'addr': addr,
                    'netmask': '64',  # Assume /64 as it's common
                    'scope': '0'
                }]
            
            # Parse MAC address
            mac_pattern = r'Physical Address[^:]*:\s+([0-9A-F-]+)'
            mac_match = re.search(mac_pattern, interface_section)
            
            if mac_match:
                mac = mac_match.group(1).replace('-', ':').lower()
                
                result[AF_LINK] = [{
                    'addr': mac,
                    'broadcast': 'ff:ff:ff:ff:ff:ff'
                }]
        
        except Exception as e:
            logger.error(f"Error getting addresses for {interface}: {e}")
        
        return result
    
    def _windows_gateways() -> Dict[str, Any]:
        result = {'default': {}}
        try:
            output = subprocess.check_output(['ipconfig'], universal_newlines=True)
            
            # Find default gateway
            gateway_pattern = r'Default Gateway[^:]*:\s+(\d+\.\d+\.\d+\.\d+)'
            gateway_matches = re.findall(gateway_pattern, output)
            
            if gateway_matches:
                # Use the first gateway found
                gw = gateway_matches[0]
                
                # Find associated interface (this is approximate)
                iface_map = {}
                
                # Get all interfaces and their IPv4 addresses
                for iface in interfaces():
                    addrs = ifaddresses(iface)
                    if AF_INET in addrs:
                        for addr_info in addrs[AF_INET]:
                            iface_map[addr_info['addr']] = iface
                
                # Use the first interface as fallback
                ifaces = interfaces()
                dev = ifaces[0] if ifaces else ''
                iface_index = 0
                
                result['default'][AF_INET] = (gw, dev, iface_index)
        
        except Exception as e:
            logger.error(f"Error getting gateways: {e}")
        
        return result

    # Helper functions
    def _prefix_to_netmask(prefix: int) -> str:
        """Convert a prefix length to a dotted-quad netmask."""
        mask = (0xffffffff << (32 - prefix)) & 0xffffffff
        return f"{mask >> 24}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"
    
    def _hex_to_dotted_quad(hex_str: str) -> str:
        """Convert a hexadecimal netmask to dotted-quad format."""
        mask = int(hex_str, 16)
        return f"{mask >> 24}.{(mask >> 16) & 0xff}.{(mask >> 8) & 0xff}.{mask & 0xff}"

# Export a module-level function for checking if this is the fallback implementation
def is_fallback() -> bool:
    """Check if we're using the fallback implementation."""
    return 'real_netifaces' not in globals()

# Export a module-level function to test the implementation
def test_implementation() -> None:
    """Test the netifaces implementation and print results."""
    print("Testing netifaces implementation...")
    print(f"Using fallback: {is_fallback()}")
    
    try:
        print("\nAvailable interfaces:")
        ifaces = interfaces()
        for iface in ifaces:
            print(f"  - {iface}")
        
        if ifaces:
            print(f"\nAddresses for {ifaces[0]}:")
            addrs = ifaddresses(ifaces[0])
            for family, addr_list in addrs.items():
                family_name = {
                    AF_INET: "IPv4",
                    AF_INET6: "IPv6",
                    AF_LINK: "MAC"
                }.get(family, str(family))
                
                print(f"  {family_name}:")
                for addr in addr_list:
                    print(f"    {addr}")
        
        print("\nGateways:")
        gws = gateways()
        for gw_type, gw_info in gws.items():
            print(f"  {gw_type}:")
            for family, info in gw_info.items():
                family_name = {
                    AF_INET: "IPv4",
                    AF_INET6: "IPv6"
                }.get(family, str(family))
                
                print(f"    {family_name}: {info}")
    
    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    test_implementation() 