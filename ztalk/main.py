import time
import socket
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
        
    def start(self, port=5000):
        # Start server
        self.server = ZTalkServer(port, self.handle_message)
        self.server.start()
        
        # Advertise service
        self.zt_zeroconf.advertise_service(self.hostname, port)
        
        # Start discovery
        self.zt_zeroconf.discover_services()
        
        print(f"ZTalk started as {self.hostname}. Press Ctrl+C to exit.")
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
                self._print_status()
                recipient = input("Enter recipient (ALL for broadcast): ")
                message = input("Enter message: ")
                
                if recipient.upper() == "ALL":
                    self.server.broadcast(f"{self.hostname}: {message}")
                else:
                    peer = self.peers.get(recipient)
                    if peer:
                        if not self.client.send(peer['ip'], f"{self.hostname}: {message}"):
                            print(f"Failed to send to {recipient}")
                    else:
                        print("Invalid recipient")
        except KeyboardInterrupt:
            self.zt_zeroconf.shutdown()
            print("\nZTalk shutdown complete")
            
    def _print_status(self):
        print("\nConnected peers:")
        for name, peer in self.peers.items():
            print(f"  {name} ({peer['ip']})")
        print("-------------------")

if __name__ == "__main__":
    app = ZTalkApp()
    app.start()