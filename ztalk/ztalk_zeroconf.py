import socket
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser, ServiceListener

class ZTalkServiceListener(ServiceListener):
    def __init__(self, app):
        self.app = app
        
    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            peer_ip = socket.inet_ntoa(info.addresses[0])
            peer_name = info.name.split('.')[0]
            self.app.add_peer({
                'name': peer_name,
                'ip': peer_ip,
                'port': info.port,
                'service_type': type_
            })

    def remove_service(self, zc, type_, name):
        peer_name = name.split('.')[0]
        self.app.remove_peer(peer_name)

class ZTalkZeroConf:
    def __init__(self, app):
        self.zeroconf = Zeroconf()
        self.app = app
        self.service_info = None
        self.service_type = "_ztalk._tcp.local."
        
    def advertise_service(self, name, port):
        local_ip = self.app.local_ip
        if not local_ip:
            raise ValueError("Could not determine local IP address")
        
        self.service_info = ServiceInfo(
            self.service_type,
            f"{name}.{self.service_type}",
            addresses=[socket.inet_aton(local_ip)],
            port=port,
            properties={'version': '1.0', 'hostname': socket.gethostname()},
        )
        self.zeroconf.register_service(self.service_info)
        
    def discover_services(self):
        listener = ZTalkServiceListener(self.app)
        self.browser = ServiceBrowser(self.zeroconf, self.service_type, listener)
        
    def shutdown(self):
        self.zeroconf.unregister_service(self.service_info)
        self.zeroconf.close()