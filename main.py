import socket
import time
import threading
from core.network_manager import NetworkManager
from core.service_discovery import ServiceDiscovery
from core.messaging import TCPServer, UDPMulticast
from utils.helpers import get_user_input, display_help

class ZTalkApp:
    def __init__(self):
        self.network_mgr = NetworkManager()
        self.service_discovery = ServiceDiscovery(self.network_mgr)
        self.tcp_server = TCPServer()
        self.udp_multicast = UDPMulticast(self.network_mgr)
        self.username = None
        self.running = False
        self._network_ready = threading.Event()
        self._network_timeout = 15  # Reduced timeout for quicker feedback

    def _network_change_handler(self, interfaces):
        if interfaces:
            print(f"\nDetected active interfaces: {list(interfaces.keys())}")
            print(f"IP addresses: {list(interfaces.values())}")
            self._network_ready.set()
        else:
            print("\nNo active network interfaces found!")
            self._network_ready.clear()

    def _initialize_services(self):
        """Initialize all network services with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"\nInitializing services (attempt {attempt + 1}/{max_retries})...")
                
                # Start TCP server
                self.tcp_server.start(self._handle_tcp_message)
                print(f"TCP server started on port {self.tcp_server.port}")
                
                # Register Zeroconf service
                self.service_discovery.register_service(self.username, self.tcp_server.port)
                self.service_discovery.browse_services()
                print("Service discovery initialized")
                
                # Start UDP multicast
                self.udp_multicast.start(self._handle_udp_message)
                print("UDP multicast started")
                
                return True
                
            except Exception as e:
                print(f"Service initialization failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait before retrying
                    continue
                return False

    def _handle_tcp_message(self, ip, message):
        print(f"\n[Private from {ip}]: {message}")

    def _handle_udp_message(self, ip, message):
        print(f"\n[Broadcast from {ip}]: {message}")

    def _send_private_message(self, username, message):
        if username not in self.service_discovery.peers:
            print(f"User {username} not found")
            return
            
        ip, port = self.service_discovery.peers[username]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((ip, port))
                s.send(f"[From {self.username}]: {message}".encode())
        except Exception as e:
            print(f"Failed to send message: {e}")
            del self.service_discovery.peers[username]

    def _input_handler(self):
        while self.running:
            try:
                command = input("> ").strip()
                if not command:
                    continue
                    
                if command == "/list":
                    print("\nConnected peers:")
                    for user in self.service_discovery.peers:
                        print(f" - {user}")
                        
                elif command.startswith("/msg "):
                    parts = command.split(maxsplit=2)
                    if len(parts) < 3:
                        print("Usage: /msg <username> <message>")
                        continue
                    self._send_private_message(parts[1], parts[2])
                    
                elif command.startswith("/broadcast "):
                    message = command[len("/broadcast "):]
                    self.udp_multicast.send(f"[Broadcast from {self.username}]: {message}")
                    
                elif command == "/quit":
                    self.shutdown()
                    
                elif command == "/help":
                    display_help()
                    
                else:
                    print("Unknown command. Type /help for available commands")
                    
            except (KeyboardInterrupt, EOFError):
                self.shutdown()
                break
            except Exception as e:
                print(f"Input error: {e}")

    def run(self):
        print("\nStarting ZTalk Application")
        print("Initializing network monitor...")
        
        # Start network monitoring
        self.network_mgr.start()
        self.network_mgr.add_interface_change_listener(self._network_change_handler)
        
        # Force immediate network check
        self.network_mgr._update_interfaces()
        
        # Check current network status
        current_ips = self.network_mgr.get_all_active_ips()
        if current_ips:
            print(f"\nActive network interfaces found with IPs: {current_ips}")
            self._network_ready.set()
        else:
            print("\nNo network interfaces with IP addresses detected")
            print("Waiting for network connection...")
            if not self._network_ready.wait(timeout=self._network_timeout):
                print("\nTimeout: No network connection established")
                print("Note: The app will still try to use link-local addresses if available")
                self._network_ready.set()  # Proceed anyway for link-local

        # Get username
        self.username = get_user_input("\nEnter your username: ")
        
        # Initialize services
        if not self._initialize_services():
            print("\nFailed to initialize network services!")
            self.shutdown()
            return

        self.running = True
        print("\nZTalk successfully started!")
        print("Type /help for available commands\n")
        
        # Start input thread
        input_thread = threading.Thread(target=self._input_handler, daemon=True)
        input_thread.start()

        # Main loop
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()
            
        input_thread.join()

    def shutdown(self):
        if not self.running:
            return
            
        self.running = False
        print("\nShutting down services...")
        
        # Stop network manager first
        self.network_mgr.stop()
        
        # Stop services in reverse initialization order
        self.udp_multicast.stop()
        self.tcp_server.stop()
        self.service_discovery.shutdown()
        
        # Wait a brief moment for threads to finish
        time.sleep(0.5)
        print("All services stopped. Goodbye!\n")

if __name__ == "__main__":
    app = ZTalkApp()
    app.run()