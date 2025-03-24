import socket
import threading

class TCPServer:
    def __init__(self, port=0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', port))
        self.port = self.sock.getsockname()[1]
        self.running = False

    def start(self, message_handler):
        self.running = True
        self.sock.listen(5)
        self.thread = threading.Thread(target=self._listen, args=(message_handler,))
        self.thread.start()

    def _listen(self, message_handler):
        while self.running:
            try:
                client, addr = self.sock.accept()
                data = client.recv(1024).decode()
                message_handler(addr[0], data)
                client.close()
            except OSError:
                break

    def stop(self):
        self.running = False
        self.sock.close()
        self.thread.join()

class UDPMulticast:
    def __init__(self, network_manager):
        self.network_manager = network_manager
        self.multicast_group = '239.255.255.250'
        self.port = 5000
        self.sock = None
        self.running = False

    def start(self, message_handler):
        self.running = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', self.port))
        
        ip = self.network_manager.get_active_interface_ip()
        if ip:
            self.sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                socket.inet_aton(self.multicast_group) + socket.inet_aton(ip)
            )
            
        self.thread = threading.Thread(target=self._listen, args=(message_handler,))
        self.thread.start()

    def _listen(self, message_handler):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                message_handler(addr[0], data.decode())
            except OSError:
                break

    def send(self, message):
        ip = self.network_manager.get_active_interface_ip()
        if ip:
            self.sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_MULTICAST_IF,
                socket.inet_aton(ip)
            )
            self.sock.sendto(message.encode(), (self.multicast_group, self.port))

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()
        self.thread.join()