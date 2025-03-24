from core.network_manager import NetworkManager
from core.service_discovery import ServiceDiscovery
from core.messaging import TCPServer, UDPMulticast
from utils.helpers import get_user_input, display_help
import threading

class ZTalkApp:
    def __init__(self):
        self.network_mgr = NetworkManager()
        self.service_discovery = ServiceDiscovery(self.network_mgr)
        self.tcp_server = TCPServer()
        self.udp_multicast = UDPMulticast(self.network_mgr)
        self.username = None
        self.running = False

    def _network_change_handler(self, new_ip):
        if new_ip:
            print("\nReinitializing services with new IP...")
            self._restart_services()
        else:
            print("\nNetwork connection lost! Trying to reconnect...")

    def _restart_services(self):
        self.service_discovery.shutdown()
        self.tcp_server.stop()
        self.udp_multicast.stop()
        
        self.service_discovery = ServiceDiscovery(self.network_mgr)
        self._initialize_services()

    def _initialize_services(self):
        # Start TCP server
        self.tcp_server.start(self._handle_tcp_message)
        
        # Register Zeroconf service
        try:
            self.service_discovery.register_service(self.username, self.tcp_server.port)
            self.service_discovery.browse_services()
        except RuntimeError as e:
            print(f"Service registration failed: {e}")
            self.shutdown()
            return False
        
        # Start UDP multicast
        self.udp_multicast.start(self._handle_udp_message)
        
        # Add network change listener
        self.network_mgr.add_interface_change_listener(self._network_change_handler)
        return True

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
                s.connect((ip, port))
                s.send(f"[From {self.username}]: {message}".encode())
        except Exception as e:
            print(f"Failed to send message: {e}")
            del self.service_discovery.peers[username]

    def run(self):
        if not self.network_mgr.validate_network():
            print("No network connection available!")
            return

        self.username = get_user_input("Enter your username: ")
        self.network_mgr.start()
        
        if not self._initialize_services():
            return

        self.running = True
        print("App started. Type /help for commands")
        
        while self.running:
            try:
                command = get_user_input("> ")
                
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
                    break
                    
                elif command == "/help":
                    display_help()
                    
                else:
                    print("Unknown command. Type /help for available commands")
                    
            except KeyboardInterrupt:
                break

        self.shutdown()

    def shutdown(self):
        self.running = False
        print("\nShutting down...")
        self.service_discovery.shutdown()
        self.tcp_server.stop()
        self.udp_multicast.stop()
        self.network_mgr.stop()

if __name__ == "__main__":
    app = ZTalkApp()
    app.run()