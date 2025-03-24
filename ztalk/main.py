import time
import socket
import netifaces
from ztalk_zeroconf import ZTalkZeroConf
from ztalk_server import ZTalkServer
from ztalk_client import ZTalkClient

class ZTalkApp:
    def __init__(self):
        self.peers = {}
        self.zt_zeroconf = ZTalkZeroConf(self)
        self.server = None
        self.client = ZTalkClient(self.handle_message)
        self.hostname = socket.gethostname()
        self.local_ip = self._get_dhcp_ip() or socket.gethostbyname(socket.gethostname())
        
    def start(self, port=5000):
        # Start server
        self.server = ZTalkServer(port, self.handle_message)
        self.server.start()
        
        # Advertise service
        self.zt_zeroconf.advertise_service(self.hostname, port)
        
        # Start discovery
        self.zt_zeroconf.discover_services()
        
        print(f"ZTalk started as {self.hostname} ({self.local_ip}). Press Ctrl+C to exit.")
        self._user_interface()
        
    def add_peer(self, peer):
        if peer['name'] not in self.peers:
            print(f"\n[+] {peer['name']} joined the network")
        self.peers[peer['name']] = peer
        self.client.connect(peer)
        
    def remove_peer(self, peer_name):
        if peer_name in self.peers:
            del self.peers[peer_name]
            print(f"\n[-] {peer_name} left the network")
            
    def handle_message(self, sender_ip, message):
        sender_name = next(
            (p['name'] for p in self.peers.values() if p['ip'] == sender_ip),
            sender_ip
        )
        print(f"\n[{sender_name}] {message}")
        
    def _user_interface(self):
        try:
            while True:
                print("\n===== ZTalk Menu =====")
                print("1. List Connected Devices")
                print("2. Group Chat")
                print("3. Private Chat")
                print("4. Exit")
                choice = input("Enter your choice: ").strip()

                if choice == '1':
                    self._print_status()
                elif choice == '2':
                    message = input("Enter group message: ")
                    self.server.broadcast(f"[GROUP] {self.hostname}: {message}")
                elif choice == '3':
                    recipient = input("Enter recipient name: ")
                    message = input("Enter private message: ")
                    peer = self.peers.get(recipient)
                    if peer:
                        success = self.client.send(peer['ip'], f"[PRIVATE] {self.hostname}: {message}")
                        if not success:
                            print(f"Failed to send to {recipient}")
                    else:
                        print("Invalid recipient")
                elif choice == '4':
                    break
                else:
                    print("Invalid choice")
        except KeyboardInterrupt:
            self.zt_zeroconf.shutdown()
            print("\nZTalk shutdown complete")
            
    def _print_status(self):
        print("\nConnected peers:")
        for name, peer in self.peers.items():
            print(f"  {name} ({peer['ip']})")
        print("-------------------")

    def _get_dhcp_ip(self):
        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for addr in addrs[netifaces.AF_INET]:
                    ip = addr['addr']
                    if ip.startswith('192.168.77.'):
                        return ip
        return None

if __name__ == "__main__":
    app = ZTalkApp()
    app.start()