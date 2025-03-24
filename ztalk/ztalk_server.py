import socket
import threading

class ZTalkServer:
    def __init__(self, port, message_handler):
        self.port = port
        self.message_handler = message_handler
        self.running = False
        self.connections = []
        
    def start(self):
        self.running = True
        thread = threading.Thread(target=self._run_server)
        thread.daemon = True
        thread.start()
        
    def _run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            s.bind(('0.0.0.0', self.port))
            s.listen()
            
            while self.running:
                conn, addr = s.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(conn, addr)
                )
                client_thread.start()
                self.connections.append(conn)
                
    def _handle_client(self, conn, addr):
        with conn:
            while self.running:
                try:
                    data = conn.recv(1024)
                    if data:
                        self.message_handler(addr[0], data.decode())
                except:
                    break
        self.connections.remove(conn)
        
    def broadcast(self, message):
        for conn in self.connections:
            try:
                conn.sendall(message.encode())
            except:
                self.connections.remove(conn)
                
    def unicast(self, target_ip, message):
        for conn in self.connections:
            if conn.getpeername()[0] == target_ip:
                try:
                    conn.sendall(message.encode())
                    return True
                except:
                    self.connections.remove(conn)
        return False