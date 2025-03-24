import socket
import threading
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener
import sys
import select
import time

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class PeerListener(ServiceListener):
    def __init__(self):
        self.peers = {}

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            addr = socket.inet_ntoa(info.addresses[0])
            port = info.port
            user = info.properties.get(b'user', b'unknown').decode('utf-8')
            self.peers[user] = (addr, port)
            print(f"\n[+] Discovered {user} at {addr}:{port}")

    def remove_service(self, zc, type_, name):
        user = name.split('.')[0]
        if user in self.peers:
            del self.peers[user]
            print(f"\n[-] {user} left")

    def update_service(self, zc, type_, name):
        pass

class TCPServer:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('', 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(5)

    def run(self):
        while True:
            client_sock, addr = self.sock.accept()
            data = client_sock.recv(1024).decode()
            print(f"\n[Message from {addr[0]}]: {data}")
            client_sock.close()

class UDPListener:
    def __init__(self, multicast_group, port):
        self.multicast_group = multicast_group
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', port))
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                            socket.inet_aton(multicast_group) + socket.inet_aton('0.0.0.0'))

    def run(self):
        while True:
            data, addr = self.sock.recvfrom(1024)
            print(f"\n[Broadcast from {addr[0]}]: {data.decode()}")

def input_thread():
    # Remove this function as we don't need a separate thread for the prompt
    pass

def main():
    username = input("Enter your username: ")
    local_ip = get_local_ip()

    # TCP Server setup
    tcp_server = TCPServer()
    tcp_thread = threading.Thread(target=tcp_server.run, daemon=True)
    tcp_thread.start()

    # Zeroconf Service Registration
    service_type = "_message._tcp.local."
    service_name = f"{username}.{service_type}"
    service_info = ServiceInfo(
        service_type,
        service_name,
        addresses=[socket.inet_aton(local_ip)],
        port=tcp_server.port,
        properties={b'user': username.encode('utf-8')},
    )
    zeroconf = Zeroconf()
    zeroconf.register_service(service_info)

    # Service Browser setup
    listener = PeerListener()
    browser = ServiceBrowser(zeroconf, service_type, listener)

    # UDP Broadcast setup
    multicast_group = '239.255.255.250'
    udp_port = 5000
    udp_listener = UDPListener(multicast_group, udp_port)
    udp_thread = threading.Thread(target=udp_listener.run, daemon=True)
    udp_thread.start()

    # UDP Sender setup
    udp_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sender.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    print("\nAvailable commands:")
    print("/list - Show connected peers")
    print("/msg <username> <message> - Send private message")
    print("/broadcast <message> - Send message to all")
    print("/quit - Exit program\n")

    while True:
        try:
            command = input("> ").strip()
            if not command:
                continue

            if command == '/list':
                print("\nConnected peers:")
                for user in listener.peers:
                    print(f" - {user}")
                    
            elif command.startswith('/msg '):
                parts = command.split(' ', 2)
                if len(parts) < 3:
                    print("Usage: /msg <username> <message>")
                    continue
                target_user, message = parts[1], parts[2]
                if target_user not in listener.peers:
                    print(f"User {target_user} not found")
                    continue
                ip, port = listener.peers[target_user]
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((ip, port))
                        s.send(f"[From {username}]: {message}".encode())
                except Exception as e:
                    print(f"Error sending message: {e}")

            elif command.startswith('/broadcast '):
                message = command[len('/broadcast '):]
                udp_sender.sendto(f"[Broadcast from {username}]: {message}".encode(), 
                                 (multicast_group, udp_port))
                
            elif command == '/quit':
                break
                
            else:
                print("Unknown command. Available commands:")
                print("/list - Show connected peers")
                print("/msg <username> <message> - Send private message")
                print("/broadcast <message> - Send message to all")
                print("/quit - Exit program")
                
        except KeyboardInterrupt:
            break

    # Cleanup
    zeroconf.unregister_service(service_info)
    zeroconf.close()
    udp_sender.close()
    print("\nGoodbye!")

if __name__ == "__main__":
    main()