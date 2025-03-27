"""
ZTalk Core Package

Provides the main components for the ZTalk application:
- ZTalkApp: The main application class
- NetworkManager: Handles network interfaces and connection
- PeerDiscovery: Discovers other ZTalk instances on the network
- ZTalkPeer: Represents a discovered peer
- MessageHandler: Handles sending and receiving messages
- Message: Represents a chat message
- MessageType: Enum of different message types
- SSHManager: Manages SSH connections
- SSHConnection: Represents a single SSH connection
- SSHConnectionStatus: Status of an SSH connection
"""

from core.application import ZTalkApp
from core.network_manager import NetworkManager
from core.peer_discovery import PeerDiscovery, ZTalkPeer
from core.messaging import MessageHandler, Message, MessageType
from core.ssh_manager import SSHManager, SSHConnection, SSHConnectionStatus

__version__ = "1.0.0"

__all__ = [
    'ZTalkApp',
    'NetworkManager',
    'PeerDiscovery',
    'ZTalkPeer',
    'MessageHandler',
    'Message',
    'MessageType',
    'SSHManager',
    'SSHConnection',
    'SSHConnectionStatus'
]
