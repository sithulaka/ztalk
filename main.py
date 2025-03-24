# A peer-to-peer chat application using Zeroconf for service discovery
# and socket programming for communication between peers.
# Standard library imports for networking and threading
import socket
import threading
import time
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener

# Constants for service configuration
SERVICE_TYPE = "_chat._tcp.local."
SERVICE_NAME = "MyChatService._chat._tcp.local."
PORT = 5000

def get_local_ip():
    """Get the actual Wi-Fi IP address of the local machine.
    Returns local IP if successful, localhost if failed."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return "127.0.0.1"

class BonjourChat:
    """Main class handling chat functionality including service advertisement,
    discovery, and communication between peers."""
    
    def __init__(self):
        """Initialize Zeroconf and required variables."""
        self.zeroconf = Zeroconf()
        self.service_info = None
        self.peer_address = None
        self.peer_port = None
        self.running = True
        self.local_ip = get_local_ip()

    def advertise_service(self):
        """Advertise this chat service on the local network using Zeroconf."""
        desc = {'version': '1.0'}
        self.service_info = ServiceInfo(
            SERVICE_TYPE,
            SERVICE_NAME,
            addresses=[socket.inet_aton(self.local_ip)],
            port=PORT,
            properties=desc,
        )
        self.zeroconf.register_service(self.service_info)
        print(f"Advertising service at {self.local_ip}:{PORT}")

    def discover_services(self):
        """Discover other chat services on the local network.
        
        Creates a ChatListener to handle service discovery events and
        runs the ServiceBrowser in a separate thread."""
        
        class ChatListener(ServiceListener):
            """Inner class to handle Zeroconf service discovery events."""
            def __init__(self, outer):
                self.outer = outer

            def add_service(self, zc, type_, name):
                info = zc.get_service_info(type_, name)
                if info:
                    peer_ip = socket.inet_ntoa(info.addresses[0])
                    if peer_ip != self.outer.local_ip:
                        self.outer.peer_address = peer_ip
                        self.outer.peer_port = info.port
                        print(f"Discovered peer: {peer_ip}:{info.port}")

        class AsyncServiceBrowser(threading.Thread):
            """Inner class to run the ServiceBrowser asynchronously."""
            def __init__(self, zeroconf, service_type, listener):
                super().__init__()
                self.browser = ServiceBrowser(zeroconf, service_type, listener)

            def run(self):
                pass

        listener = ChatListener(self)
        browser_thread = AsyncServiceBrowser(self.zeroconf, SERVICE_TYPE, listener)
        browser_thread.start()

    def start_chat(self):
        """Start the chat application by launching server and client threads.
        
        Starts a server thread immediately and launches a client thread
        once a peer is discovered."""
        server_thread = threading.Thread(target=self.run_server)
        server_thread.daemon = True
        server_thread.start()

        while self.peer_address is None and self.running:
            time.sleep(1)

        if self.peer_address:
            client_thread = threading.Thread(target=self.run_client)
            client_thread.daemon = True
            client_thread.start()

    def run_server(self):
        """Run the chat server to accept incoming connections.
        
        Creates a TCP socket server that listens for incoming connections
        and spawns a new thread for each connected client."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', PORT))
            s.listen()
            print(f"Server listening on port {PORT}...")
            while self.running:
                try:
                    conn, addr = s.accept()
                    print(f"Connected to {addr}")
                    threading.Thread(target=self.handle_client, args=(conn,)).start()
                except Exception as e:
                    print(f"Server error: {e}")

    def handle_client(self, conn):
        """Handle individual client connections.
        
        Args:
            conn: Socket connection object for the client
        """
        with conn:
            while True:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break
                    print(f"Peer says: {data.decode()}")
                except:
                    break

    def run_client(self):
        """Run the chat client to connect to the peer.
        
        Attempts to connect to the discovered peer with multiple retries
        and handles sending messages to the peer."""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(5)
                    print(f"Connecting to {self.peer_address}:{self.peer_port}...")
                    s.connect((self.peer_address, self.peer_port))
                    print("Connected! Type a message and press Enter.")
                    while True:
                        message = input("You: ")
                        s.sendall(message.encode())
                    break
            except Exception as e:
                print(f"Connection failed (attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(2)
        else:
            print("Failed to connect after multiple attempts.")

    def shutdown(self):
        """Clean up resources and shutdown the chat application."""
        self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()
        self.running = False

if __name__ == "__main__":
    """Main entry point of the application."""
    chat = BonjourChat()
    try:
        chat.advertise_service()
        chat.discover_services()
        chat.start_chat()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        chat.shutdown()