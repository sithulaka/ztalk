import socket
import threading

class ZTalkClient:
    def __init__(self, message_handler):
        self.message_handler = message_handler
        self.connections = {}
        
    def connect(self, peer):
        if peer['ip'] in self.connections:
            return False
            
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            sock.connect((peer['ip'], peer['port']))
            self.connections[peer['ip']] = sock
            threading.Thread(
                target=self._listen_for_messages,
                args=(sock, peer['ip'])
            ).start()
            return True
        except:
            return False
            
    def _listen_for_messages(self, sock, ip):
        with sock:
            while True:
                try:
                    data = sock.recv(1024)
                    if not data:
                        break
                    self.message_handler(ip, data.decode())
                except:
                    break
        del self.connections[ip]
        
    def send(self, target_ip, message):
        if target_ip in self.connections:
            try:
                self.connections[target_ip].sendall(message.encode())
                return True
            except:
                del self.connections[target_ip]
        return False