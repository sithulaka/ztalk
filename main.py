import socket
import threading
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
import time

# Configuration
SERVICE_TYPE = "_chat._tcp.local."
SERVICE_NAME = "MyChatService._chat._tcp.local."
PORT = 5000

class BonjourChat:
    def __init__(self):
        self.zeroconf = Zeroconf()
        self.service_info = None
        self.peer_address = None
        self.peer_port = None
        self.running = True
        self.local_ip = socket.gethostbyname(socket.gethostname())  # Store local IP

    def advertise_service(self):
        hostname = socket.gethostname()
        local_ip = self.local_ip
        
        desc = {'version': '1.0'}
        self.service_info = ServiceInfo(
            SERVICE_TYPE,
            SERVICE_NAME,
            addresses=[socket.inet_aton(local_ip)],
            port=PORT,
            properties=desc,
        )
        self.zeroconf.register_service(self.service_info)
        print(f"Advertising service at {local_ip}:{PORT}")

    def discover_services(self):
        class ChatListener(ServiceListener):
            def __init__(self, outer):
                self.outer = outer
                self.local_ip = outer.local_ip  # Use the parent's local IP

            def add_service(self, zc, type_, name):
                info = zc.get_service_info(type_, name)
                if info:
                    peer_ip = socket.inet_ntoa(info.addresses[0])
                    # Skip self-discovery
                    if peer_ip != self.local_ip:
                        self.outer.peer_address = peer_ip
                        self.outer.peer_port = info.port
                        print(f"Discovered peer: {peer_ip}:{info.port}")

        listener = ChatListener(self)
        browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, listener)

    def start_chat(self):
        """Start the chat client/server."""
        # Start server to listen for incoming messages
        server_thread = threading.Thread(target=self.run_server)
        server_thread.start()

        # Wait for peer discovery
        while self.peer_address is None and self.running:
            time.sleep(1)

        if self.peer_address:
            # Start client to send messages
            client_thread = threading.Thread(target=self.run_client)
            client_thread.start()

    def run_server(self):
        """Listen for incoming messages."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', PORT))
            s.listen()
            print(f"Server listening on port {PORT}...")
            conn, addr = s.accept()
            with conn:
                print(f"Connected to {addr}")
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    print(f"Peer says: {data.decode()}")

    def run_client(self):
        """Send messages to the peer."""
        time.sleep(2)  # Wait for connection
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.peer_address, self.peer_port))
            print("Connected! Type a message and press Enter.")
            while True:
                message = input("You: ")
                s.sendall(message.encode())

    def shutdown(self):
        """Cleanup."""
        self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()
        self.running = False

if __name__ == "__main__":
    chat = BonjourChat()
    try:
        chat.advertise_service()
        chat.discover_services()
        chat.start_chat()
    except KeyboardInterrupt:
        chat.shutdown()