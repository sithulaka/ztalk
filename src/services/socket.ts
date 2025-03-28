import { io, Socket } from 'socket.io-client';

// Event types
export type PeerEvent = 'connected' | 'disconnected';
export type MessageEvent = 'private' | 'broadcast' | 'group';

// Event interfaces
export interface PeerEventData {
  event: PeerEvent;
  peerId: string;
  name: string;
  ipAddress: string;
  timestamp: number;
}

export interface MessageEventData {
  messageId: string;
  type: MessageEvent;
  content: string;
  senderId: string;
  senderName: string;
  recipientId?: string;
  groupId?: string;
  timestamp: number;
}

export interface NetworkChangeEventData {
  event: 'added' | 'removed' | 'changed';
  interfaceName: string;
  oldIp?: string;
  newIp?: string;
}

export interface DHCPEventData {
  event: 'enabled' | 'disabled' | 'lease_added' | 'lease_expired';
  data: any;
}

export interface SSHEventData {
  event: 'connected' | 'disconnected' | 'error';
  connectionId: string;
  data: any;
}

// Socket service class
class SocketService {
  private socket: Socket | null = null;
  private url: string = process.env.REACT_APP_SOCKET_URL || 'http://localhost:5000';
  private connected: boolean = false;
  
  // Event callbacks
  private peerCallbacks: ((data: PeerEventData) => void)[] = [];
  private messageCallbacks: ((data: MessageEventData) => void)[] = [];
  private networkCallbacks: ((data: NetworkChangeEventData) => void)[] = [];
  private dhcpCallbacks: ((data: DHCPEventData) => void)[] = [];
  private sshCallbacks: ((data: SSHEventData) => void)[] = [];
  
  // Connect to WebSocket server
  connect(token?: string): Promise<boolean> {
    return new Promise((resolve, reject) => {
      try {
        // Initialize socket connection
        this.socket = io(this.url, {
          transports: ['websocket'],
          auth: token ? { token } : undefined,
          reconnection: true,
          reconnectionDelay: 1000,
          reconnectionAttempts: 10
        });
        
        // Setup event listeners
        this.socket.on('connect', () => {
          console.log('Socket connected');
          this.connected = true;
          resolve(true);
        });
        
        this.socket.on('disconnect', () => {
          console.log('Socket disconnected');
          this.connected = false;
        });
        
        this.socket.on('error', (error) => {
          console.error('Socket error:', error);
          reject(error);
        });
        
        // Register handlers for our specific events
        this.socket.on('peer_event', (data: PeerEventData) => {
          this.peerCallbacks.forEach(callback => callback(data));
        });
        
        this.socket.on('message_event', (data: MessageEventData) => {
          this.messageCallbacks.forEach(callback => callback(data));
        });
        
        this.socket.on('network_change', (data: NetworkChangeEventData) => {
          this.networkCallbacks.forEach(callback => callback(data));
        });
        
        this.socket.on('dhcp_event', (data: DHCPEventData) => {
          this.dhcpCallbacks.forEach(callback => callback(data));
        });
        
        this.socket.on('ssh_event', (data: SSHEventData) => {
          this.sshCallbacks.forEach(callback => callback(data));
        });
        
      } catch (error) {
        console.error('Failed to connect to WebSocket server:', error);
        reject(error);
        return false;
      }
    });
  }
  
  // Disconnect from server
  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
    }
  }
  
  // Check connection status
  isConnected(): boolean {
    return this.connected;
  }
  
  // Register event handlers
  onPeerEvent(callback: (data: PeerEventData) => void): void {
    this.peerCallbacks.push(callback);
  }
  
  onMessageEvent(callback: (data: MessageEventData) => void): void {
    this.messageCallbacks.push(callback);
  }
  
  onNetworkChange(callback: (data: NetworkChangeEventData) => void): void {
    this.networkCallbacks.push(callback);
  }
  
  onDHCPEvent(callback: (data: DHCPEventData) => void): void {
    this.dhcpCallbacks.push(callback);
  }
  
  onSSHEvent(callback: (data: SSHEventData) => void): void {
    this.sshCallbacks.push(callback);
  }
  
  // Unregister event handlers
  offPeerEvent(callback: (data: PeerEventData) => void): void {
    this.peerCallbacks = this.peerCallbacks.filter(cb => cb !== callback);
  }
  
  offMessageEvent(callback: (data: MessageEventData) => void): void {
    this.messageCallbacks = this.messageCallbacks.filter(cb => cb !== callback);
  }
  
  offNetworkChange(callback: (data: NetworkChangeEventData) => void): void {
    this.networkCallbacks = this.networkCallbacks.filter(cb => cb !== callback);
  }
  
  offDHCPEvent(callback: (data: DHCPEventData) => void): void {
    this.dhcpCallbacks = this.dhcpCallbacks.filter(cb => cb !== callback);
  }
  
  offSSHEvent(callback: (data: SSHEventData) => void): void {
    this.sshCallbacks = this.sshCallbacks.filter(cb => cb !== callback);
  }
}

// Create and export singleton instance
export const socketService = new SocketService();
export default socketService; 