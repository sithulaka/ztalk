"""
Messaging System for ZTalk

Handles communication between peers, message routing, and delivery guarantees.
Supports both group and private messages with encryption.
"""

import socket
import threading
import time
import json
import logging
import uuid
import queue
import hashlib
import base64
from typing import Dict, List, Set, Optional, Callable, Any, Tuple
from datetime import datetime
from enum import Enum, auto

# Optional encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages that can be sent"""
    CHAT = auto()        # Regular chat message
    SYSTEM = auto()      # System notification
    PRESENCE = auto()    # User presence update
    FILE = auto()        # File transfer
    COMMAND = auto()     # Remote command (SSH related)
    PING = auto()        # Network connectivity test
    ACK = auto()         # Message acknowledgment
    

class Message:
    """Represents a message in the ZTalk system"""
    
    def __init__(self, 
                 sender_id: str,
                 sender_name: str,
                 content: str,
                 msg_type: MessageType = MessageType.CHAT,
                 recipient_id: Optional[str] = None,
                 group_id: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        
        self.id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.sender_name = sender_name
        self.content = content
        self.msg_type = msg_type
        self.recipient_id = recipient_id  # For private messages
        self.group_id = group_id          # For group messages
        self.timestamp = time.time()
        self.metadata = metadata or {}
        self.delivered = False
        self.read = False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization"""
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "content": self.content,
            "msg_type": self.msg_type.name,
            "recipient_id": self.recipient_id,
            "group_id": self.group_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "delivered": self.delivered,
            "read": self.read
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        msg = cls(
            sender_id=data["sender_id"],
            sender_name=data["sender_name"],
            content=data["content"],
            msg_type=MessageType[data["msg_type"]],
            recipient_id=data.get("recipient_id"),
            group_id=data.get("group_id"),
            metadata=data.get("metadata", {})
        )
        msg.id = data["id"]
        msg.timestamp = data["timestamp"]
        msg.delivered = data.get("delivered", False)
        msg.read = data.get("read", False)
        return msg
    
    def __str__(self):
        """String representation for debugging"""
        target = self.recipient_id if self.recipient_id else f"Group({self.group_id})" if self.group_id else "All"
        return f"Message({self.id[:8]}): {self.sender_name} -> {target}: {self.content[:20]}..."


class MessageHandler:
    """
    Handles the core messaging operations including:
    - Message sending and receiving over the network
    - Message history management
    - Delivery guarantees and acknowledgements
    """
    
    # Protocol constants
    DEFAULT_PORT = 8990
    BUFFER_SIZE = 4096
    MESSAGE_HISTORY_LIMIT = 1000
    RETRY_ATTEMPTS = 3
    RETRY_DELAY = 2.0  # seconds
    
    def __init__(self, peer_id: str, username: str, port: int = DEFAULT_PORT):
        # Core identity
        self.peer_id = peer_id
        self.username = username
        self.port = port
        
        # Network components
        self.socket = None
        self.server_thread = None
        self.running = False
        
        # Message handling
        self.outgoing_queue = queue.Queue()
        self.sender_thread = None
        self.message_handlers: List[Callable[[Message], None]] = []
        self.pending_acks: Dict[str, Message] = {}  # Messages waiting for acknowledgment
        
        # Message history - stores recent messages
        self.message_history: List[Message] = []
        self.private_histories: Dict[str, List[Message]] = {}  # peer_id -> message history
        self.group_histories: Dict[str, List[Message]] = {}    # group_id -> message history
        
        # Encryption
        self.encryption_enabled = False
        self.encryption_key = None
        
    def start(self):
        """Start the message handler"""
        if self.running:
            return True
            
        try:
            # Set up the socket for receiving messages
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.port))
            
            # Start listener thread
            self.running = True
            self.server_thread = threading.Thread(target=self._message_listener, daemon=True)
            self.server_thread.start()
            
            # Start message sender thread
            self.sender_thread = threading.Thread(target=self._message_sender, daemon=True)
            self.sender_thread.start()
            
            logger.info(f"Message handler started on port {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting message handler: {e}")
            self.running = False
            return False
    
    def stop(self):
        """Stop the message handler"""
        self.running = False
        
        # Close the socket to unblock the listener
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            
        # Wait for threads to end
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)
            
        if self.sender_thread and self.sender_thread.is_alive():
            self.sender_thread.join(timeout=1.0)
            
        logger.info("Message handler stopped")
        return True
    
    def add_message_handler(self, handler: Callable[[Message], None]):
        """Add a callback to handle incoming messages"""
        self.message_handlers.append(handler)
        
    def remove_message_handler(self, handler: Callable[[Message], None]):
        """Remove a message handler"""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)
    
    def send_message(self, 
                    content: str, 
                    recipient_id: Optional[str] = None, 
                    recipient_address: Optional[Tuple[str, int]] = None,
                    group_id: Optional[str] = None,
                    msg_type: MessageType = MessageType.CHAT,
                    metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Send a message to a recipient.
        Returns message ID if successful, None otherwise.
        """
        # Create message object
        message = Message(
            sender_id=self.peer_id,
            sender_name=self.username,
            content=content,
            msg_type=msg_type,
            recipient_id=recipient_id,
            group_id=group_id,
            metadata=metadata
        )
        
        # Store in appropriate history
        self._store_message(message)
        
        # If we don't have an address, we can't send
        if not recipient_address and not metadata or "broadcast" not in metadata:
            logger.warning(f"No address for message to {recipient_id or group_id}")
            return None
            
        # Queue the message for sending
        self.outgoing_queue.put((message, recipient_address))
        
        return message.id
    
    def send_direct_message(self, 
                           content: str, 
                           peer_id: str, 
                           address: Tuple[str, int],
                           msg_type: MessageType = MessageType.CHAT,
                           metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Send a direct (private) message to a peer"""
        return self.send_message(
            content=content, 
            recipient_id=peer_id, 
            recipient_address=address,
            msg_type=msg_type,
            metadata=metadata
        )
    
    def send_group_message(self, 
                          content: str, 
                          group_id: str,
                          addresses: List[Tuple[str, int]],
                          msg_type: MessageType = MessageType.CHAT,
                          metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Send a message to a group.
        The same message is sent to all addresses in the group.
        """
        message = Message(
            sender_id=self.peer_id,
            sender_name=self.username,
            content=content,
            msg_type=msg_type,
            group_id=group_id,
            metadata=metadata
        )
        
        # Store in group history
        self._store_message(message)
        
        # Queue the message for each recipient
        for address in addresses:
            self.outgoing_queue.put((message, address))
            
        return message.id
    
    def broadcast_message(self, 
                         content: str,
                         addresses: List[Tuple[str, int]],
                         msg_type: MessageType = MessageType.CHAT,
                         metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Broadcast a message to all known peers"""
        if not metadata:
            metadata = {}
        metadata["broadcast"] = True
        
        message = Message(
            sender_id=self.peer_id,
            sender_name=self.username,
            content=content,
            msg_type=msg_type,
            metadata=metadata
        )
        
        # Store in general history
        self._store_message(message)
        
        # Queue the message for each recipient
        for address in addresses:
            self.outgoing_queue.put((message, address))
            
        return message.id
    
    def get_message_history(self, limit: int = 50) -> List[Message]:
        """Get recent messages from the general history"""
        return self.message_history[-limit:] if self.message_history else []
    
    def get_private_history(self, peer_id: str, limit: int = 50) -> List[Message]:
        """Get message history with a specific peer"""
        if peer_id not in self.private_histories:
            return []
        return self.private_histories[peer_id][-limit:] if self.private_histories[peer_id] else []
    
    def get_group_history(self, group_id: str, limit: int = 50) -> List[Message]:
        """Get message history for a specific group"""
        if group_id not in self.group_histories:
            return []
        return self.group_histories[group_id][-limit:] if self.group_histories[group_id] else []
    
    def clear_history(self, peer_id: Optional[str] = None, group_id: Optional[str] = None):
        """Clear message history"""
        if peer_id:
            if peer_id in self.private_histories:
                self.private_histories[peer_id] = []
        elif group_id:
            if group_id in self.group_histories:
                self.group_histories[group_id] = []
        else:
            self.message_history = []
    
    # Encryption methods
    def enable_encryption(self, password: str) -> bool:
        """Enable message encryption with a password"""
        if not ENCRYPTION_AVAILABLE:
            logger.warning("Encryption requested but cryptography package not available")
            return False
            
        try:
            # Generate a key from the password
            salt = b'ZTalk_salt_value'  # This should be randomly generated and shared
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            self.encryption_key = key
            self.encryption_enabled = True
            logger.info("Encryption enabled")
            return True
        except Exception as e:
            logger.error(f"Error enabling encryption: {e}")
            return False
    
    def disable_encryption(self):
        """Disable message encryption"""
        self.encryption_enabled = False
        self.encryption_key = None
        logger.info("Encryption disabled")
        
    # Private methods
    def _message_listener(self):
        """Background thread that listens for incoming messages"""
        logger.debug("Message listener started")
        
        while self.running:
            try:
                # Set a timeout so we can check if we're still running
                self.socket.settimeout(0.5)
                
                try:
                    # Wait for a message
                    data, addr = self.socket.recvfrom(self.BUFFER_SIZE)
                    
                    # Process the message
                    message = self._process_incoming_message(data, addr)
                    if message:
                        # Notify handlers
                        for handler in self.message_handlers:
                            try:
                                handler(message)
                            except Exception as e:
                                logger.error(f"Error in message handler: {e}")
                        
                        # Send acknowledgment for chat messages if requested
                        if message.msg_type == MessageType.CHAT and message.metadata.get("needs_ack"):
                            self._send_acknowledgment(message, addr)
                            
                except socket.timeout:
                    # This is expected, just continue the loop
                    pass
                    
                except Exception as e:
                    if self.running:  # Only log if we're still supposed to be running
                        logger.error(f"Error receiving message: {e}")
                    
            except Exception as e:
                if self.running:
                    logger.error(f"Error in message listener: {e}")
                    time.sleep(1)  # Avoid tight loop if there's a persistent error
    
    def _message_sender(self):
        """Background thread that sends queued messages"""
        logger.debug("Message sender started")
        
        while self.running:
            try:
                # Get a message from the queue (with timeout to check if we're still running)
                try:
                    message, addr = self.outgoing_queue.get(timeout=0.5)
                    
                    # Send the message
                    self._send_message_to_address(message, addr)
                    
                    # Mark the task as done
                    self.outgoing_queue.task_done()
                    
                except queue.Empty:
                    # This is expected, just continue the loop
                    pass
                    
            except Exception as e:
                if self.running:
                    logger.error(f"Error in message sender: {e}")
                    time.sleep(1)  # Avoid tight loop if there's a persistent error
    
    def _process_incoming_message(self, data: bytes, addr: Tuple[str, int]) -> Optional[Message]:
        """Process an incoming message"""
        try:
            # Decrypt if necessary
            if self.encryption_enabled and self.encryption_key:
                try:
                    f = Fernet(self.encryption_key)
                    data = f.decrypt(data)
                except Exception as e:
                    logger.warning(f"Failed to decrypt message from {addr}: {e}")
                    return None
            
            # Parse the JSON data
            message_dict = json.loads(data.decode('utf-8'))
            
            # Create a Message object
            message = Message.from_dict(message_dict)
            
            # Check if this is an ACK
            if message.msg_type == MessageType.ACK:
                # Find the original message that's being acknowledged
                ack_id = message.metadata.get("ack_for")
                if ack_id and ack_id in self.pending_acks:
                    original_msg = self.pending_acks.pop(ack_id)
                    original_msg.delivered = True
                    logger.debug(f"Message {ack_id[:8]} acknowledged by {message.sender_id}")
                return None  # Don't forward ACK messages to handlers
            
            # Store the message in appropriate history
            self._store_message(message)
            
            return message
            
        except json.JSONDecodeError:
            logger.warning(f"Received invalid JSON data from {addr}")
            return None
        except Exception as e:
            logger.error(f"Error processing message from {addr}: {e}")
            return None
    
    def _send_message_to_address(self, message: Message, addr: Tuple[str, int]) -> bool:
        """Send a message to a specific address"""
        try:
            # Convert message to JSON
            message_data = json.dumps(message.to_dict()).encode('utf-8')
            
            # Encrypt if necessary
            if self.encryption_enabled and self.encryption_key:
                try:
                    f = Fernet(self.encryption_key)
                    message_data = f.encrypt(message_data)
                except Exception as e:
                    logger.error(f"Failed to encrypt message: {e}")
                    return False
            
            # Send the message
            self.socket.sendto(message_data, addr)
            
            # If needs acknowledgment, store in pending
            if message.metadata.get("needs_ack") and message.msg_type == MessageType.CHAT:
                self.pending_acks[message.id] = message
                
                # Start a timer to retry if no ACK received
                threading.Timer(self.RETRY_DELAY, self._check_ack, args=[message.id, addr, 1]).start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending message to {addr}: {e}")
            return False
    
    def _check_ack(self, message_id: str, addr: Tuple[str, int], attempt: int):
        """Check if a message has been acknowledged, retry if not"""
        if message_id not in self.pending_acks:
            # Message has been acknowledged, nothing to do
            return
            
        if attempt >= self.RETRY_ATTEMPTS:
            # Max attempts reached, give up
            logger.warning(f"Message {message_id[:8]} not acknowledged after {attempt} attempts")
            # Could notify UI here
            return
            
        # Retry sending the message
        logger.debug(f"Retrying message {message_id[:8]}, attempt {attempt+1}")
        message = self.pending_acks[message_id]
        self._send_message_to_address(message, addr)
        
        # Schedule another check
        threading.Timer(self.RETRY_DELAY, self._check_ack, args=[message_id, addr, attempt+1]).start()
    
    def _send_acknowledgment(self, message: Message, addr: Tuple[str, int]):
        """Send an acknowledgment for a received message"""
        ack = Message(
            sender_id=self.peer_id,
            sender_name=self.username,
            content="",
            msg_type=MessageType.ACK,
            recipient_id=message.sender_id,
            metadata={"ack_for": message.id}
        )
        
        # Send directly, don't queue
        self._send_message_to_address(ack, addr)
    
    def _store_message(self, message: Message):
        """Store a message in the appropriate history"""
        # Store in general history for all except ACKs
        if message.msg_type != MessageType.ACK:
            self.message_history.append(message)
            # Trim if needed
            if len(self.message_history) > self.MESSAGE_HISTORY_LIMIT:
                self.message_history = self.message_history[-self.MESSAGE_HISTORY_LIMIT:]
        
        # Store in private history if it's a private message
        if message.recipient_id or message.sender_id != self.peer_id:
            peer_id = message.recipient_id if message.sender_id == self.peer_id else message.sender_id
            if peer_id:
                if peer_id not in self.private_histories:
                    self.private_histories[peer_id] = []
                    
                self.private_histories[peer_id].append(message)
                
                # Trim if needed
                if len(self.private_histories[peer_id]) > self.MESSAGE_HISTORY_LIMIT:
                    self.private_histories[peer_id] = self.private_histories[peer_id][-self.MESSAGE_HISTORY_LIMIT:]
        
        # Store in group history if it's a group message
        if message.group_id:
            if message.group_id not in self.group_histories:
                self.group_histories[message.group_id] = []
                
            self.group_histories[message.group_id].append(message)
            
            # Trim if needed
            if len(self.group_histories[message.group_id]) > self.MESSAGE_HISTORY_LIMIT:
                self.group_histories[message.group_id] = self.group_histories[message.group_id][-self.MESSAGE_HISTORY_LIMIT:]