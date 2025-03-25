import socket
import time
import threading
import argparse
import platform
import sys
import os
from core.network_manager import NetworkManager
from core.service_discovery import ServiceDiscovery
from core.messaging import TCPServer, UDPMulticast
from utils.helpers import get_user_input
from ui import ChatWindow

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='ZTalk - Cross-platform P2P Chat Application')
    parser.add_argument('--username', type=str, help='Username to use (skips prompt)')
    parser.add_argument('--no-gui', action='store_true', help='Run in command-line mode (no GUI)')
    parser.add_argument('--portable', action='store_true', help='Run in portable mode (data stored in app directory)')
    return parser.parse_args()

class ZTalkApp:
    def __init__(self, args=None):
        self.args = args or parse_arguments()
        self.network_mgr = NetworkManager()
        self.service_discovery = ServiceDiscovery(self.network_mgr)
        self.tcp_server = TCPServer()
        self.udp_multicast = UDPMulticast(self.network_mgr)
        self.username = self.args.username
        self.running = False
        self._network_ready = threading.Event()
        self._network_timeout = 15
        self.chat_window = None
        
        # Setup app directories for cross-platform use
        self.setup_app_dirs()

    def setup_app_dirs(self):
        """Set up application directories for data storage"""
        system = platform.system()
        app_name = "ZTalk"
        
        if self.args.portable:
            # Use local directory for portable mode
            self.app_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
        else:
            # Use platform-specific data directories
            if system == "Windows":
                self.app_dir = os.path.join(os.environ.get("APPDATA", ""), app_name)
            elif system == "Darwin":  # macOS
                self.app_dir = os.path.expanduser(f"~/Library/Application Support/{app_name}")
            else:  # Linux and other Unix-like systems
                self.app_dir = os.path.expanduser(f"~/.config/{app_name}")
                
        # Create directory if it doesn't exist
        os.makedirs(self.app_dir, exist_ok=True)

    def _network_change_handler(self, interfaces):
        if interfaces:
            if self.chat_window:
                self.chat_window.add_system_message(f"Network interfaces updated: {list(interfaces.keys())}")
            self._network_ready.set()
        else:
            if self.chat_window:
                self.chat_window.add_system_message("No active network interfaces found!")
            self._network_ready.clear()

    def _initialize_services(self):
        """Initialize all network services with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if self.chat_window:
                    self.chat_window.add_system_message(f"Initializing services (attempt {attempt + 1}/{max_retries})...")
                
                # Start TCP server
                self.tcp_server.start(self._handle_tcp_message)
                
                # Register Zeroconf service
                self.service_discovery.register_service(self.username, self.tcp_server.port)
                self.service_discovery.browse_services()
                
                # Start UDP multicast
                self.udp_multicast.start(self._handle_udp_message)
                
                if self.chat_window:
                    self.chat_window.add_system_message("All services initialized successfully!")
                return True
                
            except Exception as e:
                if self.chat_window:
                    self.chat_window.add_system_message(f"Service initialization failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return False

    def _handle_tcp_message(self, ip, message):
        if self.chat_window:
            self.chat_window.add_message("Private", message)

    def _handle_udp_message(self, ip, message):
        if self.chat_window:
            self.chat_window.add_message("Broadcast", message)

    def _send_private_message(self, username, message):
        # Get username from the chat window if needed
        if not self.username and self.chat_window:
            self.username = self.chat_window.username
            
        if username not in self.service_discovery.peers:
            if self.chat_window:
                self.chat_window.add_system_message(f"User {username} not found")
            return
            
        ip, port = self.service_discovery.peers[username]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((ip, port))
                s.send(f"[From {self.username}]: {message}".encode())
        except Exception as e:
            if self.chat_window:
                self.chat_window.add_system_message(f"Failed to send message: {e}")
            del self.service_discovery.peers[username]

    def get_peers(self):
        return list(self.service_discovery.peers.keys())

    def run(self):
        print("Starting ZTalk Application")
        print("Initializing network monitor...")
        
        # Start network monitoring
        self.network_mgr.start()
        self.network_mgr.add_interface_change_listener(self._network_change_handler)
        
        # Force immediate network check
        self.network_mgr._update_interfaces()
        
        # Check current network status
        current_ips = self.network_mgr.get_all_active_ips()
        if current_ips:
            print(f"Active network interfaces found with IPs: {current_ips}")
            self._network_ready.set()
        else:
            print("No network interfaces with IP addresses detected")
            print("Waiting for network connection...")
            if not self._network_ready.wait(timeout=self._network_timeout):
                print("Timeout: No network connection established")
                print("Note: The app will still try to use link-local addresses if available")
                self._network_ready.set()

        # Create UI - username will be asked within the UI
        self.chat_window = ChatWindow(
            username=self.username,  # This can be None now, UI will ask
            send_private_msg=self._send_private_message,
            send_broadcast=self.udp_multicast.send,
            get_peers=self.get_peers,
            network_manager=self.network_mgr
        )
        
        # Set up a callback when username is set
        self.chat_window.on_username_set = self._on_username_set
        
        # Start the UI - will ask for username
        try:
            self.chat_window.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()
            
    def _on_username_set(self, username):
        """Called when username is set in the UI"""
        self.username = username
        print(f"Username set: {username}")
        
        # Now initialize network services with the username
        if self._initialize_services():
            if self.chat_window:
                self.chat_window.add_system_message(f"ZTalk started successfully! Your username: {username}")
                self.chat_window.add_system_message(f"Running on {platform.system()} {platform.release()}")
        else:
            if self.chat_window:
                self.chat_window.add_system_message("Failed to initialize network services!")
                
    def shutdown(self):
        """Shut down all network services and close the application"""
        if not hasattr(self, 'running'):
            self.running = True  # Set this so the shutdown can proceed
            
        print("Shutting down ZTalk application...")
        
        # Stop network services
        try:
            if hasattr(self, 'udp_multicast'):
                print("Stopping UDP multicast...")
                self.udp_multicast.stop()
        except Exception as e:
            print(f"Error stopping UDP multicast: {e}")
            
        try:
            if hasattr(self, 'tcp_server'):
                print("Stopping TCP server...")
                self.tcp_server.stop()
        except Exception as e:
            print(f"Error stopping TCP server: {e}")
            
        try:
            if hasattr(self, 'service_discovery'):
                print("Shutting down service discovery...")
                self.service_discovery.shutdown()
        except Exception as e:
            print(f"Error shutting down service discovery: {e}")
            
        try:
            if hasattr(self, 'network_mgr'):
                print("Stopping network manager...")
                self.network_mgr.stop()
        except Exception as e:
            print(f"Error stopping network manager: {e}")
            
        # Wait a moment for threads to finish
        print("Waiting for threads to finish...")
        time.sleep(0.5)
        
        # If chat window exists, destroy it
        if hasattr(self, 'chat_window') and self.chat_window:
            try:
                print("Destroying chat window...")
                self.chat_window.destroy()
            except Exception as e:
                print(f"Error destroying chat window: {e}")
                
        print("Shutdown complete.")
                
        # Force termination if necessary
        try:
            if platform.system() != "Windows":
                os.kill(os.getpid(), signal.SIGKILL)
            else:
                # On Windows we can use os._exit
                os._exit(0)
        except:
            # Last resort
            sys.exit(0)

if __name__ == "__main__":
    app = ZTalkApp()
    app.run()
def main():
    """Entry point for the application"""
    try:
        args = parse_arguments()
        app = ZTalkApp(args)
        app.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
