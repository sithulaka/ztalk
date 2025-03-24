from scapy.all import *
from scapy.layers.dhcp import DHCP, BOOTP
from scapy.layers.inet import UDP, IP
import threading
import time
import netifaces

class ZTalkDHCPServer:
    def __init__(self, interface, pool_range=("192.168.77.2", "192.168.77.254"), 
                 subnet_mask="255.255.255.0", gateway="192.168.77.1"):
        self.interface = interface
        self.pool_start = pool_range[0]
        self.pool_end = pool_range[1]
        self.subnet_mask = subnet_mask
        self.gateway = gateway
        self.leases = {}
        self.running = False
        self.lease_time = 3600  # 1 hour

    def start(self):
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.start()
        print(f"[DHCP] Server started on {self.interface}")

    def _run_server(self):
        sniff(filter="udp and (port 67 or 68)", prn=self._handle_packet, store=0)

    def _handle_packet(self, packet):
        if DHCP in packet:
            mac = packet[Ether].src
            if packet[DHCP].options[0][1] == 1:  # Discover
                self._send_offer(packet, mac)
            elif packet[DHCP].options[0][1] == 3:  # Request
                self._send_ack(packet, mac)

    def _send_offer(self, packet, mac):
        if mac not in self.leases:
            self.leases[mac] = self._next_available_ip()

        offer = (Ether(dst=packet[Ether].src, src=get_if_hwaddr(self.interface)) /
                IP(src=self.gateway, dst="255.255.255.255") /
                UDP(sport=67, dport=68) /
                BOOTP(op=2, yiaddr=self.leases[mac], siaddr=self.gateway, chaddr=packet[BOOTP].chaddr) /
                DHCP(options=[("message-type", "offer"),
                             ("subnet_mask", self.subnet_mask),
                             ("router", self.gateway),
                             ("lease_time", self.lease_time),
                             "end"]))
        sendp(offer, iface=self.interface, verbose=0)

    def _send_ack(self, packet, mac):
        ack = (Ether(dst=packet[Ether].src, src=get_if_hwaddr(self.interface)) /
              IP(src=self.gateway, dst="255.255.255.255") /
              UDP(sport=67, dport=68) /
              BOOTP(op=2, yiaddr=self.leases[mac], siaddr=self.gateway, chaddr=packet[BOOTP].chaddr) /
              DHCP(options=[("message-type", "ack"),
                           ("subnet_mask", self.subnet_mask),
                           ("router", self.gateway),
                           ("lease_time", self.lease_time),
                           "end"]))
        sendp(ack, iface=self.interface, verbose=0)

    def _next_available_ip(self):
        start = list(map(int, self.pool_start.split(".")))
        end = list(map(int, self.pool_end.split(".")))
        
        for a in range(start[0], end[0]+1):
            for b in range(start[1], end[1]+1):
                for c in range(start[2], end[2]+1):
                    for d in range(start[3], end[3]+1):
                        ip = f"{a}.{b}.{c}.{d}"
                        if ip not in self.leases.values():
                            return ip
        return None

    def stop(self):
        self.running = False
        self.server_thread.join()

def run_dhcp_server():
    interfaces = netifaces.interfaces()
    target_iface = None
    for iface in interfaces:
        if iface.startswith('eth') or iface.startswith('wlan'):
            target_iface = iface
            break
            
    if target_iface:
        dhcp_server = ZTalkDHCPServer(target_iface)
        dhcp_server.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            dhcp_server.stop()
            print("\n[DHCP] Server stopped.")
    else:
        print("No suitable network interface found.")

if __name__ == "__main__":
    run_dhcp_server()