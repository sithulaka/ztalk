import socket
import threading
import logging
from typing import Callable, List, Optional

class TCPServer:
    def __init__(self):
        self.logger = logging.getLogger('TCPServer')
        self.sock = None
        self.port = None
        self.running = False
        self._init_socket()

    def _init_socket(self):
        """Initialize TCP socket with error handling"""
        try:
            if self.sock:
                self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('0.0.0.0', 0))
            self.port = self.sock.getsockname()[1]
        except Exception as e:
            self.logger.error(f"Failed to initialize socket: {e}")
            raise

    def start(self, message_handler: Callable):
        """Start listening for TCP connections"""
        if not self.sock:
            self._init_socket()
        self.running = True
        self.sock.listen(5)
        threading.Thread(target=self._accept_connections, args=(message_handler,), daemon=True).start()

    def _accept_connections(self, message_handler: Callable):
        while self.running:
            try:
                client, addr = self.sock.accept()
                data = client.recv(1024).decode()
                message_handler(addr[0], data)
                client.close()
            except OSError:
                break

    def stop(self):
        """Stop TCP server"""
        self.running = False
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

class UDPMulticast:
    def __init__(self, network_manager):
        self.logger = logging.getLogger('UDPMulticast')
        self.network_manager = network_manager
        self.multicast_group = '239.255.255.250'
        self.port = 5000
        self.sockets: List[socket.socket] = []
        self.running = False
        self.thread = None  # Add thread reference

    def start(self, message_handler: Callable):
        """Start listening on all interfaces"""
        self.running = True
        # Use _active_interfaces instead of active_interfaces
        for interface, ip in self.network_manager._active_interfaces.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(('', self.port))
                
                # Interface-specific multicast
                sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_MULTICAST_IF,
                    socket.inet_aton(ip)
                )
                sock.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    socket.inet_aton(self.multicast_group) + socket.inet_aton(ip)
                )
                
                self.thread = threading.Thread(target=self._listen, args=(sock, message_handler))
                self.thread.daemon = True
                self.thread.start()
                self.sockets.append(sock)
            except Exception as e:
                print(f"Failed to start UDP multicast on {interface}: {e}")
                continue

    def _listen(self, sock: socket.socket, handler: Callable):
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                handler(addr[0], data.decode())
            except OSError:
                break

    def send(self, message: str):
        """Send multicast message through all interfaces"""
        # Use _active_interfaces instead of active_interfaces
        for interface, ip in self.network_manager._active_interfaces.items():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.setsockopt(
                        socket.IPPROTO_IP,
                        socket.IP_MULTICAST_IF,
                        socket.inet_aton(ip)
                    )
                    s.sendto(message.encode(), (self.multicast_group, self.port))
            except Exception as e:
                print(f"Failed to send multicast on {interface}: {e}")
                continue

    def stop(self):
        """Stop UDP listeners"""
        self.running = False
        for sock in self.sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                sock.close()
            except:
                pass
        self.sockets.clear()
        
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=1.0)
            except:
                pass