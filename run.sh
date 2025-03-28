#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print colored message
print_message() {
    echo -e "${GREEN}[ZTalk]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[ZTalk Warning]${NC} $1"
}

print_error() {
    echo -e "${RED}[ZTalk Error]${NC} $1"
}

# Detect if we're on Kali Linux
detect_kali_linux() {
    if [ -f "/etc/os-release" ]; then
        if grep -q "kali" /etc/os-release; then
            return 0 # true, we're on Kali
        fi
    fi
    return 1 # false, not on Kali
}

# Create and activate virtual environment
setup_virtual_env() {
    # Check if already in a virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        # Force recreation of virtual environment if it's broken
        if [ -d ".venv" ] && [ ! -f ".venv/bin/pip" ]; then
            print_warning "Existing virtual environment is broken. Recreating..."
            rm -rf .venv
        fi
        
        # Check if virtual environment exists
        if [ -d ".venv" ]; then
            print_message "Activating existing virtual environment..."
            source .venv/bin/activate
        else
            print_message "Creating new virtual environment..."
            
            # On Kali Linux make sure pypy3-venv is installed
            if detect_kali_linux; then
                if ! dpkg -l | grep -q pypy3-venv; then
                    print_warning "pypy3-venv not detected. Attempting to install..."
                    print_message "You may need to enter your password for sudo:"
                    sudo apt-get update && sudo apt-get install -y pypy3-venv
                fi
            fi
            
            python3 -m venv .venv
            source .venv/bin/activate
            
            # Initialize pip in the new environment
            print_message "Setting up pip in virtual environment..."
            if detect_kali_linux; then
                python -m ensurepip --upgrade --break-system-packages
            else
                python -m ensurepip --upgrade
            fi
        fi
    else
        print_message "Using active virtual environment: $VIRTUAL_ENV"
    fi
    
    # Verify activation worked
    if [ -z "$VIRTUAL_ENV" ]; then
        print_error "Failed to activate virtual environment. Manual activation may be required."
        print_message "Try running: source .venv/bin/activate"
        exit 1
    fi
}

# Install dependencies
install_dependencies() {
    print_message "Installing dependencies..."
    
    # Upgrade pip first
    if detect_kali_linux; then
        python -m pip install --upgrade pip --break-system-packages
        # Install required packages
        python -m pip install -r requirements.txt --break-system-packages
    else
        python -m pip install --upgrade pip
        # Install required packages
        python -m pip install -r requirements.txt
    fi
    
    # Check if netifaces installed successfully
    if ! python -c "import netifaces" &>/dev/null; then
        print_warning "netifaces package installation failed. Setting up compatibility layer..."
        
        # Ensure compatibility modules exist
        if [ ! -f "netifaces_compat.py" ]; then
            print_warning "Creating netifaces compatibility module..."
            cat > netifaces_compat.py << 'EOF'
import socket
import os
import platform
import logging
import re
from typing import Dict, List, Optional, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("netifaces_compat")

# Constants that match netifaces
AF_INET = 2
AF_INET6 = 30
AF_LINK = 18
AF_PACKET = 17  # Linux specific

# Flag to indicate we're using fallback implementation
_is_fallback = True

def is_fallback() -> bool:
    """Returns True if we're using the fallback implementation"""
    return _is_fallback

def interfaces() -> List[str]:
    """Return a list of network interface names"""
    if platform.system() == "Linux":
        # Use /proc/net/dev on Linux
        try:
            with open("/proc/net/dev", "r") as f:
                # Skip header lines
                f.readline()
                f.readline()
                interfaces = []
                for line in f:
                    # Extract interface name (everything before the colon)
                    iface = line.split(":", 1)[0].strip()
                    if iface and not iface.startswith("lo"):
                        interfaces.append(iface)
                return interfaces
        except Exception as e:
            logger.error(f"Error reading /proc/net/dev: {e}")
    
    # Fallback: Use socket.if_nameindex() available in Python 3.3+
    try:
        return [iface[1] for iface in socket.if_nameindex() if iface[1] != "lo"]
    except Exception as e:
        logger.error(f"Error with socket.if_nameindex(): {e}")
        
    # Last resort
    return ["eth0", "wlan0"]  # Return common interface names

def ifaddresses(interface: str) -> Dict[int, List[Dict[str, str]]]:
    """Get the addresses for an interface"""
    result = {}
    
    if platform.system() == "Linux":
        # For Linux, use ip addr show
        try:
            import subprocess
            output = subprocess.check_output(["ip", "addr", "show", interface], 
                                             universal_newlines=True)
            
            # Extract MAC address
            mac_match = re.search(r"link/\w+ ([0-9a-f:]{17})", output)
            if mac_match:
                result[AF_LINK] = [{"addr": mac_match.group(1)}]
            
            # Extract IPv4 addresses
            ipv4_matches = re.finditer(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", output)
            if ipv4_matches:
                ipv4_list = []
                for match in ipv4_matches:
                    ipv4_list.append({
                        "addr": match.group(1),
                        "netmask": _cidr_to_netmask(int(match.group(2)))
                    })
                if ipv4_list:
                    result[AF_INET] = ipv4_list
            
            # Extract IPv6 addresses
            ipv6_matches = re.finditer(r"inet6 ([0-9a-f:]+)/(\d+)", output)
            if ipv6_matches:
                ipv6_list = []
                for match in ipv6_matches:
                    ipv6_list.append({
                        "addr": match.group(1),
                        "netmask": _cidr6_to_netmask(int(match.group(2)))
                    })
                if ipv6_list:
                    result[AF_INET6] = ipv6_list
                    
            return result
            
        except Exception as e:
            logger.warning(f"Error using ip command: {e}, trying fallback methods")
    
    # Try to get IP using socket
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # This doesn't actually send any packets
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        
        result[AF_INET] = [{"addr": ip, "netmask": "255.255.255.0"}]
    except Exception as e:
        logger.warning(f"Error getting IP with socket: {e}")
    
    return result

def gateways() -> Dict[str, Any]:
    """Get the default gateway information"""
    result = {"default": {}}
    
    if platform.system() == "Linux":
        try:
            with open("/proc/net/route", "r") as f:
                # Skip header
                f.readline()
                for line in f:
                    fields = line.strip().split()
                    if fields[1] == "00000000":  # Destination of 0.0.0.0
                        # Convert hex gateway to decimal IP
                        gw = ".".join(str(int(fields[2][i:i+2], 16)) 
                                     for i in range(6, -1, -2))
                        result["default"][AF_INET] = (gw, fields[0])
                        break
            return result
        except Exception as e:
            logger.warning(f"Error reading /proc/net/route: {e}")
    
    # Fallback
    result["default"][AF_INET] = ("192.168.1.1", "eth0")
    return result

def _cidr_to_netmask(cidr: int) -> str:
    """Convert a CIDR prefix to a netmask string"""
    mask = (0xffffffff << (32 - cidr)) & 0xffffffff
    return ".".join([str((mask >> (8 * i)) & 0xff) for i in range(3, -1, -1)])

def _cidr6_to_netmask(cidr: int) -> str:
    """Convert a CIDR prefix to an IPv6 netmask string"""
    mask_parts = []
    for i in range(0, 8):
        if cidr >= 16:
            mask_parts.append("ffff")
            cidr -= 16
        elif cidr > 0:
            mask_parts.append(f"{(0xffff << (16 - cidr)) & 0xffff:04x}")
            cidr = 0
        else:
            mask_parts.append("0000")
    return ":".join(mask_parts)
EOF
            chmod +x netifaces_compat.py
        fi
    fi
    
    # Check if zeroconf installed successfully
    if ! python -c "import zeroconf" &>/dev/null; then
        print_warning "zeroconf package installation failed. Please manually install it or use compatibility layer."
        
        # Ensure compatibility modules exist
        if [ ! -f "zeroconf_compat.py" ]; then
            print_warning "Creating simple zeroconf compatibility module (limited functionality)..."
            cat > zeroconf_compat.py << 'EOF'
"""
Simple zeroconf compatibility module

This provides minimal functionality when the zeroconf package isn't available.
It uses simple UDP broadcasts for service discovery on the local network.
"""

import socket
import threading
import json
import time
import logging
import random
from typing import Dict, List, Optional, Any, Callable

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zeroconf_compat")

# Flag to indicate we're using fallback implementation
_is_fallback = True

def is_fallback() -> bool:
    """Returns True if we're using the fallback implementation"""
    return _is_fallback

class SimpleServiceInfo:
    """Simplified version of ServiceInfo for compatibility"""
    
    def __init__(self, 
                 type_: str, 
                 name: str, 
                 addresses: Optional[List[bytes]] = None, 
                 port: Optional[int] = None,
                 properties: Optional[Dict[bytes, bytes]] = None,
                 server: Optional[str] = None):
        """Initialize the service info"""
        self.type = type_
        self.name = name
        self._addresses = addresses or []
        self.port = port
        self._properties = properties or {}
        self.server = server
        
    def parse_addresses(self) -> List[str]:
        """Parse binary addresses into strings"""
        result = []
        for addr in self._addresses:
            if len(addr) == 4:  # IPv4
                result.append(".".join(str(b) for b in addr))
        return result
    
    def properties(self) -> Dict[str, str]:
        """Get properties as string dict"""
        result = {}
        for key, value in self._properties.items():
            if isinstance(key, bytes):
                key = key.decode('utf-8', errors='replace')
            if isinstance(value, bytes):
                value = value.decode('utf-8', errors='replace')
            result[key] = value
        return result
    
    def get_name(self) -> str:
        """Get service name"""
        return self.name
    
    def get_type(self) -> str:
        """Get service type"""
        return self.type
    
    def get_addresses(self) -> List[bytes]:
        """Get binary addresses"""
        return self._addresses

class SimpleZeroconf:
    """Simple Zeroconf implementation using UDP broadcasts"""
    
    def __init__(self, interfaces=None):
        """Initialize the zeroconf instance"""
        self.interfaces = interfaces
        self.services: Dict[str, SimpleServiceInfo] = {}
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.socket: Optional[socket.socket] = None
        self.port = 5353  # mDNS port
        self.discovered_services: Dict[str, SimpleServiceInfo] = {}
        self.service_listeners: List[Any] = []
        
    def register_service(self, info: SimpleServiceInfo):
        """Register a service to be advertised"""
        logger.info(f"Registering service: {info.name}")
        self.services[info.name] = info
        
        # Start broadcasting if not already running
        if not self.running:
            self._start_broadcasting()
    
    def unregister_service(self, info: SimpleServiceInfo):
        """Unregister a service"""
        if info.name in self.services:
            logger.info(f"Unregistering service: {info.name}")
            del self.services[info.name]
    
    def close(self):
        """Stop all advertising and listening"""
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            self.thread = None
        self.services.clear()
        self.discovered_services.clear()
        self.service_listeners.clear()
    
    def add_service_listener(self, service_type: str, listener: Any):
        """Add a listener for service discovery events"""
        self.service_listeners.append((service_type, listener))
        
        # Start broadcasting if not already running
        if not self.running:
            self._start_broadcasting()
    
    def remove_service_listener(self, listener: Any):
        """Remove a service listener"""
        self.service_listeners = [item for item in self.service_listeners 
                                 if item[1] != listener]
    
    def get_service_info(self, service_type: str, service_name: str) -> Optional[SimpleServiceInfo]:
        """Get information about a service"""
        key = f"{service_name}.{service_type}"
        return self.discovered_services.get(key)
    
    def _start_broadcasting(self):
        """Start the broadcasting thread"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.socket.bind(('0.0.0.0', self.port))
            
            self.running = True
            self.thread = threading.Thread(target=self._broadcast_loop, daemon=True)
            self.thread.start()
            
            logger.info("Started zeroconf compatibility broadcasting")
        except Exception as e:
            logger.error(f"Error starting broadcasting: {e}")
            self.running = False
            if self.socket:
                self.socket.close()
                self.socket = None
    
    def _broadcast_loop(self):
        """Main broadcasting and listening loop"""
        broadcast_addr = '255.255.255.255'
        
        while self.running:
            try:
                # Broadcast our services periodically
                if self.services:
                    for service_info in self.services.values():
                        message = {
                            "type": "service_advertisement",
                            "service_type": service_info.type,
                            "service_name": service_info.name,
                            "port": service_info.port,
                            "properties": {
                                k.decode('utf-8', errors='replace') 
                                if isinstance(k, bytes) else k: 
                                v.decode('utf-8', errors='replace') 
                                if isinstance(v, bytes) else v
                                for k, v in service_info._properties.items()
                            }
                        }
                        
                        # Add addresses if available
                        if service_info._addresses:
                            message["addresses"] = [
                                ".".join(str(b) for b in addr) 
                                if len(addr) == 4 else repr(addr)
                                for addr in service_info._addresses
                            ]
                        
                        try:
                            self.socket.sendto(json.dumps(message).encode(), 
                                              (broadcast_addr, self.port))
                        except Exception as e:
                            logger.error(f"Error broadcasting service: {e}")
                
                # Check for received packets with timeout
                self.socket.settimeout(1.0)
                try:
                    data, addr = self.socket.recvfrom(4096)
                    self._handle_received_packet(data, addr)
                except socket.timeout:
                    pass  # Expected timeout
                except Exception as e:
                    logger.error(f"Error receiving packet: {e}")
                
                # Sleep a random time to avoid network congestion
                time.sleep(random.uniform(1.0, 3.0))
                
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                time.sleep(5.0)  # Back off on error
    
    def _handle_received_packet(self, data: bytes, addr: tuple):
        """Handle a received packet from the network"""
        try:
            message = json.loads(data.decode('utf-8'))
            if message.get("type") == "service_advertisement":
                service_type = message.get("service_type")
                service_name = message.get("service_name")
                port = message.get("port")
                
                if not all([service_type, service_name, port]):
                    return
                
                # Create address list
                addresses = []
                for addr_str in message.get("addresses", []):
                    try:
                        if "." in addr_str:  # IPv4
                            addresses.append(bytes([int(b) for b in addr_str.split(".")]))
                    except Exception:
                        pass
                
                # If no addresses provided, use the sender's address
                if not addresses:
                    addresses.append(bytes([int(b) for b in addr[0].split(".")]))
                
                # Create properties dict
                properties = {}
                for k, v in message.get("properties", {}).items():
                    if isinstance(k, str):
                        k = k.encode('utf-8')
                    if isinstance(v, str):
                        v = v.encode('utf-8')
                    properties[k] = v
                
                # Create service info
                info = SimpleServiceInfo(
                    type_=service_type,
                    name=service_name,
                    addresses=addresses,
                    port=port,
                    properties=properties,
                    server=addr[0]
                )
                
                # Store the service
                key = f"{service_name}.{service_type}"
                is_new = key not in self.discovered_services
                self.discovered_services[key] = info
                
                # Notify listeners
                for listener_type, listener in self.service_listeners:
                    if listener_type == service_type:
                        if is_new and hasattr(listener, 'add_service'):
                            try:
                                listener.add_service(self, service_type, service_name)
                            except Exception as e:
                                logger.error(f"Error in listener.add_service: {e}")
                        elif hasattr(listener, 'update_service'):
                            try:
                                listener.update_service(self, service_type, service_name)
                            except Exception as e:
                                logger.error(f"Error in listener.update_service: {e}")
                
        except json.JSONDecodeError:
            pass  # Not a JSON message
        except Exception as e:
            logger.error(f"Error handling packet: {e}")

# Factory function to match zeroconf API
def Zeroconf(interfaces=None):
    return SimpleZeroconf(interfaces)

# For ServiceBrowser compatibility
class ServiceBrowser:
    def __init__(self, zeroconf, service_type, handlers=None, listener=None):
        self.zeroconf = zeroconf
        self.service_type = service_type
        self.listener = listener or handlers
        
        # Add our listener to zeroconf
        zeroconf.add_service_listener(service_type, self)
    
    def cancel(self):
        if self.zeroconf:
            self.zeroconf.remove_service_listener(self)

# For ServiceInfo compatibility
def ServiceInfo(type_, name, addresses=None, port=None, properties=None, server=None):
    if isinstance(addresses, list) and all(isinstance(addr, str) for addr in addresses):
        # Convert string addresses to bytes
        binary_addrs = []
        for addr in addresses:
            if "." in addr:  # IPv4
                binary_addrs.append(bytes([int(b) for b in addr.split(".")]))
        addresses = binary_addrs
    
    return SimpleServiceInfo(type_, name, addresses, port, properties, server)
EOF
            chmod +x zeroconf_compat.py
        fi
    fi
}

# Check if required Python modules are available
check_python_modules() {
    print_message "Checking Python modules..."
    
    # Check for required modules
    MISSING_MODULES=()
    
    # Try to import each required module
    for module in netifaces zeroconf cryptography; do
        if ! python -c "import $module" &>/dev/null; then
            MISSING_MODULES+=("$module")
        fi
    done
    
    # Report missing modules
    if [ ${#MISSING_MODULES[@]} -gt 0 ]; then
        print_warning "The following Python modules are missing or couldn't be imported:"
        for module in "${MISSING_MODULES[@]}"; do
            echo "  - $module"
        done
        print_message "Will use compatibility modules where available."
    else
        print_message "All required Python modules are available."
    fi
}

# Run the application
run_app() {
    # Check which mode to run in
    if [ "$1" = "terminal" ]; then
        print_message "Starting ZTalk in terminal mode..."
        # Shift to remove the 'terminal' argument
        shift
        # Run the terminal UI version
        python main.py "$@"
    elif [ "$1" = "web" ] || [ "$1" = "react" ]; then
        print_message "Starting ZTalk in web mode (API + React)..."
        # Check if npm is installed
        if ! command -v npm &> /dev/null; then
            print_error "npm is not installed. Please install Node.js and npm to run the web version."
            exit 1
        fi
        
        # Install npm dependencies if needed
        if [ ! -d "node_modules" ]; then
            print_message "Installing npm dependencies..."
            npm install
        fi
        
        # Run the combined server (API + React)
        npm run dev
    elif [ "$1" = "api" ]; then
        print_message "Starting ZTalk API server only..."
        python app.py
    else
        # If no specific mode, decide based on arguments
        if [ $# -gt 0 ]; then
            # If they passed arguments, use ztalk.py launcher
            print_message "Running ZTalk component..."
            python ztalk.py "$@"
        else
            # Default to web mode if no arguments
            print_message "Starting ZTalk in web mode (API + React)..."
            # Check if npm is installed
            if ! command -v npm &> /dev/null; then
                print_error "npm is not installed. Please install Node.js and npm to run the web version."
                exit 1
            fi
            
            # Install npm dependencies if needed
            if [ ! -d "node_modules" ]; then
                print_message "Installing npm dependencies..."
                npm install
            fi
            
            # Run the combined server (API + React)
            npm run dev
        fi
    fi
}

# Main script
main() {
    # Show banner
    echo -e "${GREEN}"
    echo "  _______ _____ _    _ _      _  __"
    echo " |__   __|_   _/ \  | | |    | |/ /"
    echo "    | |    | || |  | | |    | ' / "
    echo "    | |    | || |__| | |___ | . \ "
    echo "    |_|    |_|\____/|_____||_|\_\\"
    echo "    "
    echo "  Zero-Configuration Networking & SSH Tool"
    echo -e "${NC}"
    
    # Setup environment and dependencies
    setup_virtual_env
    install_dependencies
    check_python_modules
    
    # Run the application with any arguments passed to this script
    run_app "$@"
}

# Run the main function with all arguments passed to the script
main "$@"