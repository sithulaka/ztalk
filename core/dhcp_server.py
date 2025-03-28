"""
DHCP Server Module for ZTalk

Provides a custom DHCP server implementation to assign IP addresses to devices
on the local network. This allows ZTalk to manage its own network segment even
when no external DHCP server is available.
"""

import socket
import struct
import threading
import logging
import ipaddress
import random
import time
from typing import Dict, List, Tuple, Optional, Set, Any

# DHCP Message Type Codes
DHCP_DISCOVER = 1
DHCP_OFFER = 2
DHCP_REQUEST = 3
DHCP_ACK = 5
DHCP_NAK = 6
DHCP_RELEASE = 7

# DHCP Option Codes
DHCP_MESSAGE_TYPE = 53
DHCP_SERVER_ID = 54
DHCP_REQUESTED_IP = 50
DHCP_LEASE_TIME = 51
DHCP_SUBNET_MASK = 1
DHCP_ROUTER = 3
DHCP_DNS = 6
DHCP_DOMAIN_NAME = 15
DHCP_END = 255

# DHCP Default Values
DEFAULT_LEASE_TIME = 86400  # 24 hours in seconds

class DHCPServer:
    """DHCP Server for automatic IP assignment on local networks"""
    
    def __init__(self, network_manager):
        """Initialize the DHCP server with a reference to the network manager"""
        self.logger = logging.getLogger('DHCPServer')
        self.network_manager = network_manager
        self.running = False
        self.socket = None
        self.thread = None
        
        # Default network settings - can be overridden
        self.network = ipaddress.IPv4Network('192.168.100.0/24')
        self.server_ip = str(self.network.network_address + 1)  # Typically .1
        self.subnet_mask = str(self.network.netmask)
        self.router = self.server_ip  # Default gateway is this server
        self.dns_servers = ['8.8.8.8', '8.8.4.4']  # Google DNS by default
        self.domain_name = 'ztalk.local'
        
        # Track IP assignments and leases
        self.leases: Dict[str, Dict[str, Any]] = {}  # mac -> {ip, lease_end, hostname}
        self.reserved_ips: Set[str] = set()  # IPs that should not be assigned

    def configure(self, network: str, server_ip: Optional[str] = None, 
                 dns_servers: Optional[List[str]] = None, 
                 domain_name: Optional[str] = None):
        """Configure the DHCP server with custom settings"""
        try:
            self.network = ipaddress.IPv4Network(network)
            self.subnet_mask = str(self.network.netmask)
            
            if server_ip:
                # Ensure server IP is within the network
                server = ipaddress.IPv4Address(server_ip)
                if server in self.network:
                    self.server_ip = server_ip
                    self.router = server_ip
                else:
                    self.logger.error(f"Server IP {server_ip} is not in network {network}")
                    raise ValueError(f"Server IP {server_ip} is not in network {network}")
            else:
                # Default to first usable IP in network
                self.server_ip = str(self.network.network_address + 1)
                self.router = self.server_ip
            
            if dns_servers:
                self.dns_servers = dns_servers
                
            if domain_name:
                self.domain_name = domain_name
                
            # Add server IP to reserved list
            self.reserved_ips.add(self.server_ip)
            
            self.logger.info(f"DHCP server configured for network {network} with server IP {self.server_ip}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure DHCP server: {e}")
            return False

    def start(self):
        """Start the DHCP server on port 67"""
        if self.running:
            self.logger.warning("DHCP server already running")
            return False
            
        try:
            # Create and configure UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Bind to all interfaces on DHCP server port
            self.socket.bind(('0.0.0.0', 67))
            
            # Start listening thread
            self.running = True
            self.thread = threading.Thread(target=self._listen_for_requests, daemon=True)
            self.thread.start()
            
            self.logger.info(f"DHCP server started on {self.server_ip}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start DHCP server: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            self.running = False
            return False
    
    def stop(self):
        """Stop the DHCP server"""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        self.logger.info("DHCP server stopped")
    
    def _listen_for_requests(self):
        """Listen for and process DHCP requests"""
        self.logger.info("DHCP server listening for requests")
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                threading.Thread(target=self._process_dhcp_packet, 
                                args=(data, addr), daemon=True).start()
            except socket.error as e:
                if self.running:  # Only log if we didn't trigger the error by stopping
                    self.logger.error(f"Socket error: {e}")
            except Exception as e:
                self.logger.error(f"Error processing DHCP packet: {e}")
    
    def _process_dhcp_packet(self, packet: bytes, addr: Tuple[str, int]):
        """Process a DHCP packet and respond accordingly"""
        try:
            # Parse DHCP packet
            if len(packet) < 240:  # Minimum DHCP packet size
                return
                
            # Extract message type and hardware address
            message_type = self._get_dhcp_message_type(packet)
            if not message_type:
                return
                
            # Get client MAC address from packet
            mac_address = self._format_mac(packet[28:34])
            
            # Handle different DHCP message types
            if message_type == DHCP_DISCOVER:
                self._handle_discover(packet, mac_address)
            elif message_type == DHCP_REQUEST:
                self._handle_request(packet, mac_address)
            elif message_type == DHCP_RELEASE:
                self._handle_release(packet, mac_address)
                
        except Exception as e:
            self.logger.error(f"Error processing DHCP packet: {e}")
    
    def _handle_discover(self, packet: bytes, mac_address: str):
        """Handle DHCP DISCOVER message by offering an IP address"""
        self.logger.info(f"Received DHCP DISCOVER from {mac_address}")
        
        # Check if client has an existing lease
        if mac_address in self.leases and not self._is_lease_expired(mac_address):
            # Offer the same IP if lease exists
            offered_ip = self.leases[mac_address]['ip']
        else:
            # Generate a new IP address offer
            offered_ip = self._get_available_ip()
            if not offered_ip:
                self.logger.error("No available IP addresses to offer")
                return
        
        # Prepare and send DHCP OFFER
        response = self._build_dhcp_response(packet, DHCP_OFFER, offered_ip)
        self._send_dhcp_packet(response)
        
        self.logger.info(f"Sent DHCP OFFER of {offered_ip} to {mac_address}")
    
    def _handle_request(self, packet: bytes, mac_address: str):
        """Handle DHCP REQUEST message by acknowledging IP assignment"""
        requested_ip = self._get_requested_ip(packet)
        
        self.logger.info(f"Received DHCP REQUEST from {mac_address} for IP {requested_ip}")
        
        # Validate request is for our server (in case of multiple DHCP servers)
        server_id = self._get_server_id(packet)
        if server_id and server_id != self.server_ip:
            self.logger.info(f"Request not for this server (ID: {server_id})")
            return
        
        # Check if IP is available or already assigned to this client
        if requested_ip:
            if (requested_ip in self.reserved_ips and 
                (mac_address not in self.leases or self.leases[mac_address]['ip'] != requested_ip)):
                # IP is reserved by another client
                self._send_dhcp_nak(packet)
                self.logger.info(f"Sent NAK - IP {requested_ip} is reserved")
            else:
                # IP is available or already assigned to this client
                lease_end = int(time.time()) + DEFAULT_LEASE_TIME
                self.leases[mac_address] = {
                    'ip': requested_ip,
                    'lease_end': lease_end,
                    'hostname': self._get_hostname(packet)
                }
                self.reserved_ips.add(requested_ip)
                
                # Send ACK
                response = self._build_dhcp_response(packet, DHCP_ACK, requested_ip)
                self._send_dhcp_packet(response)
                
                self.logger.info(f"Sent ACK - IP {requested_ip} assigned to {mac_address}")
        else:
            # Missing requested IP
            self._send_dhcp_nak(packet)
            self.logger.info(f"Sent NAK - No requested IP in packet")
    
    def _handle_release(self, packet: bytes, mac_address: str):
        """Handle DHCP RELEASE message by freeing the IP address"""
        self.logger.info(f"Received DHCP RELEASE from {mac_address}")
        
        if mac_address in self.leases:
            released_ip = self.leases[mac_address]['ip']
            self.reserved_ips.discard(released_ip)
            del self.leases[mac_address]
            self.logger.info(f"Released IP {released_ip} from {mac_address}")
    
    def _get_available_ip(self) -> Optional[str]:
        """Get an available IP address from the network pool"""
        # Start from the second address in the network (first is usually gateway)
        start_ip = int(self.network.network_address) + 10  # Skip some low IPs for manual assignment
        end_ip = int(self.network.broadcast_address) - 1
        
        # Try to find an available IP
        for ip_int in range(start_ip, end_ip + 1):
            ip = str(ipaddress.IPv4Address(ip_int))
            if ip not in self.reserved_ips:
                return ip
        
        return None
    
    def _is_lease_expired(self, mac_address: str) -> bool:
        """Check if a lease has expired"""
        if mac_address in self.leases:
            return int(time.time()) > self.leases[mac_address]['lease_end']
        return True
    
    def _send_dhcp_nak(self, request_packet: bytes):
        """Send a DHCP NAK message"""
        response = self._build_dhcp_response(request_packet, DHCP_NAK, None)
        self._send_dhcp_packet(response)
    
    def _send_dhcp_packet(self, packet: bytes):
        """Send a DHCP packet to the broadcast address"""
        try:
            self.socket.sendto(packet, ('255.255.255.255', 68))
        except Exception as e:
            self.logger.error(f"Error sending DHCP packet: {e}")
    
    def _build_dhcp_response(self, request: bytes, msg_type: int, offer_ip: Optional[str]) -> bytes:
        """Build a DHCP response packet"""
        response = bytearray(512)
        
        # Message type: Boot reply
        response[0] = 2
        
        # Hardware type: Ethernet
        response[1] = 1
        
        # Hardware address length: 6 bytes
        response[2] = 6
        
        # Hops: 0
        response[3] = 0
        
        # Transaction ID: Copy from request
        response[4:8] = request[4:8]
        
        # Seconds elapsed: 0
        response[8:10] = b'\x00\x00'
        
        # Bootp flags: 0 (Unicast)
        if request[10] & 0x80:  # Check if broadcast flag is set in request
            response[10:12] = b'\x80\x00'  # Set broadcast flag
        else:
            response[10:12] = b'\x00\x00'  # Unicast
        
        # Client IP: 0.0.0.0 for OFFER, requested IP for ACK
        if msg_type == DHCP_ACK and offer_ip:
            response[16:20] = socket.inet_aton(offer_ip)
        else:
            response[16:20] = b'\x00\x00\x00\x00'
        
        # Your (client) IP address
        if offer_ip and msg_type != DHCP_NAK:
            response[20:24] = socket.inet_aton(offer_ip)
        else:
            response[20:24] = b'\x00\x00\x00\x00'
        
        # Server IP address
        response[24:28] = socket.inet_aton(self.server_ip)
        
        # Gateway IP address: 0.0.0.0
        response[28:32] = b'\x00\x00\x00\x00'
        
        # Client MAC address: Copy from request
        response[32:38] = request[28:34]
        
        # Client hardware address padding: 10 bytes of 0
        response[38:48] = b'\x00' * 10
        
        # Server hostname: 0 bytes
        response[48:112] = b'\x00' * 64
        
        # Boot filename: 0 bytes
        response[112:240] = b'\x00' * 128
        
        # Magic cookie: DHCP
        response[240:244] = b'\x63\x82\x53\x63'
        
        # DHCP Options
        options_index = 244
        
        # Option: DHCP Message Type
        response[options_index] = DHCP_MESSAGE_TYPE
        response[options_index + 1] = 1
        response[options_index + 2] = msg_type
        options_index += 3
        
        # Option: DHCP Server Identifier
        response[options_index] = DHCP_SERVER_ID
        response[options_index + 1] = 4
        response[options_index + 2:options_index + 6] = socket.inet_aton(self.server_ip)
        options_index += 6
        
        if msg_type != DHCP_NAK:
            # Option: Subnet Mask
            response[options_index] = DHCP_SUBNET_MASK
            response[options_index + 1] = 4
            response[options_index + 2:options_index + 6] = socket.inet_aton(self.subnet_mask)
            options_index += 6
            
            # Option: Lease Time
            response[options_index] = DHCP_LEASE_TIME
            response[options_index + 1] = 4
            response[options_index + 2:options_index + 6] = struct.pack('!I', DEFAULT_LEASE_TIME)
            options_index += 6
            
            # Option: Router
            response[options_index] = DHCP_ROUTER
            response[options_index + 1] = 4
            response[options_index + 2:options_index + 6] = socket.inet_aton(self.router)
            options_index += 6
            
            # Option: Domain Name Server
            if self.dns_servers:
                response[options_index] = DHCP_DNS
                response[options_index + 1] = 4 * len(self.dns_servers)
                options_index += 2
                
                for dns in self.dns_servers:
                    response[options_index:options_index + 4] = socket.inet_aton(dns)
                    options_index += 4
            
            # Option: Domain Name
            if self.domain_name:
                response[options_index] = DHCP_DOMAIN_NAME
                domain_bytes = self.domain_name.encode('ascii')
                response[options_index + 1] = len(domain_bytes)
                response[options_index + 2:options_index + 2 + len(domain_bytes)] = domain_bytes
                options_index += 2 + len(domain_bytes)
        
        # End Option
        response[options_index] = DHCP_END
        options_index += 1
        
        return bytes(response[:options_index])
    
    def _get_dhcp_message_type(self, packet: bytes) -> Optional[int]:
        """Extract DHCP message type from packet"""
        if len(packet) < 240 or packet[240:244] != b'\x63\x82\x53\x63':
            return None
            
        # Parse options
        i = 244
        while i < len(packet):
            if packet[i] == 255:  # End option
                break
            if packet[i] == 0:  # Pad option
                i += 1
                continue
                
            if i + 1 >= len(packet):
                break
                
            opt_len = packet[i + 1]
            if i + 2 + opt_len > len(packet):
                break
                
            if packet[i] == DHCP_MESSAGE_TYPE and opt_len == 1:
                return packet[i + 2]
                
            i += 2 + opt_len
            
        return None
    
    def _get_requested_ip(self, packet: bytes) -> Optional[str]:
        """Extract requested IP from packet"""
        if len(packet) < 240 or packet[240:244] != b'\x63\x82\x53\x63':
            return None
            
        # First check if this is a DHCPREQUEST in response to DHCPOFFER
        # In that case, requested IP is in 'ciaddr' field (bytes 16-20)
        ciaddr = packet[16:20]
        if not all(b == 0 for b in ciaddr):
            return socket.inet_ntoa(ciaddr)
            
        # Otherwise, check for DHCP_REQUESTED_IP option
        i = 244
        while i < len(packet):
            if packet[i] == 255:  # End option
                break
            if packet[i] == 0:  # Pad option
                i += 1
                continue
                
            if i + 1 >= len(packet):
                break
                
            opt_len = packet[i + 1]
            if i + 2 + opt_len > len(packet):
                break
                
            if packet[i] == DHCP_REQUESTED_IP and opt_len == 4:
                return socket.inet_ntoa(packet[i + 2:i + 6])
                
            i += 2 + opt_len
            
        return None
    
    def _get_server_id(self, packet: bytes) -> Optional[str]:
        """Extract server identifier from packet"""
        if len(packet) < 240 or packet[240:244] != b'\x63\x82\x53\x63':
            return None
            
        i = 244
        while i < len(packet):
            if packet[i] == 255:  # End option
                break
            if packet[i] == 0:  # Pad option
                i += 1
                continue
                
            if i + 1 >= len(packet):
                break
                
            opt_len = packet[i + 1]
            if i + 2 + opt_len > len(packet):
                break
                
            if packet[i] == DHCP_SERVER_ID and opt_len == 4:
                return socket.inet_ntoa(packet[i + 2:i + 6])
                
            i += 2 + opt_len
            
        return None
    
    def _get_hostname(self, packet: bytes) -> Optional[str]:
        """Extract hostname from packet"""
        if len(packet) < 240 or packet[240:244] != b'\x63\x82\x53\x63':
            return None
            
        # Check for hostname option (12)
        i = 244
        while i < len(packet):
            if packet[i] == 255:  # End option
                break
            if packet[i] == 0:  # Pad option
                i += 1
                continue
                
            if i + 1 >= len(packet):
                break
                
            opt_len = packet[i + 1]
            if i + 2 + opt_len > len(packet):
                break
                
            if packet[i] == 12 and opt_len > 0:  # Hostname option
                try:
                    return packet[i + 2:i + 2 + opt_len].decode('ascii')
                except:
                    return None
                
            i += 2 + opt_len
            
        return None
    
    def _format_mac(self, mac_bytes: bytes) -> str:
        """Format MAC address bytes as a string"""
        return ':'.join(f'{b:02x}' for b in mac_bytes)
    
    def get_leases(self) -> Dict[str, Dict[str, Any]]:
        """Get current DHCP leases"""
        # Remove expired leases first
        current_time = int(time.time())
        expired = [mac for mac, lease in self.leases.items() 
                  if lease['lease_end'] < current_time]
        
        for mac in expired:
            ip = self.leases[mac]['ip']
            self.reserved_ips.discard(ip)
            del self.leases[mac]
        
        return self.leases