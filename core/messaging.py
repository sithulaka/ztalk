import socket
import threading
from typing import Callable, Dict, List

class TCPServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('0.0.0.0', 0))  # Bind to all interfaces
        self.port = self.sock.getsockname()[1]
        self.running = False

    def start(self, message_handler: Callable):
        """Start listening for TCP connections"""
        self.running = True
        self.sock.listen(5)
        threading.Thread(target=self._accept_connections, args=(message_handler,)).start()

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
        self.sock.close()

class UDPMulticast:
    def __init__(self, network_manager):
        self.network_manager = network_manager
        self.multicast_group = '239.255.255.250'
        self.port = 5000
        self.sockets: List[socket.socket] = []
        self.running = False

    def start(self, message_handler: Callable):
        """Start listening on all interfaces"""
        self.running = True
        for interface, ip in self.network_manager.active_interfaces.items():
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
            
            threading.Thread(target=self._listen, args=(sock, message_handler)).start()
            self.sockets.append(sock)

    def _listen(self, sock: socket.socket, handler: Callable):
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                handler(addr[0], data.decode())
            except OSError:
                break

    def send(self, message: str):
        """Send multicast message through all interfaces"""
        for interface, ip in self.network_manager.active_interfaces.items():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(
                    socket.IPPROTO_IP,
                    socket.IP_MULTICAST_IF,
                    socket.inet_aton(ip)
                )
                s.sendto(message.encode(), (self.multicast_group, self.port))

    def stop(self):
        """Stop UDP listeners"""
        self.running = False
        for sock in self.sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
                sock.close()
            except:
                pass
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=0.5)