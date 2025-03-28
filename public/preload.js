const { contextBridge, ipcRenderer } = require('electron');
const axios = require('axios');

// API URL for connecting to Flask backend
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

// Create API client
const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Create WebSocket connection (will be initialized later)
let socket = null;

// Helper to create API methods
const createApiMethod = (method, endpoint, transformFn) => {
  return async (...args) => {
    try {
      let response;
      
      if (method === 'GET') {
        response = await apiClient.get(endpoint, ...args);
      } else if (method === 'POST') {
        response = await apiClient.post(endpoint, ...args);
      } else if (method === 'PUT') {
        response = await apiClient.put(endpoint, ...args);
      } else if (method === 'DELETE') {
        response = await apiClient.delete(endpoint, ...args);
      }
      
      return transformFn ? transformFn(response.data) : response.data;
    } catch (error) {
      console.error(`API error (${method} ${endpoint}):`, error);
      throw error;
    }
  };
};

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld(
  'electron', {
    // Network APIs
    getNetworkInterfaces: () => ipcRenderer.invoke('get-network-interfaces'),
    getIpConfig: (interfaceName) => ipcRenderer.invoke('get-ip-config', interfaceName),
    applyIpConfig: (config) => ipcRenderer.invoke('apply-ip-config', config),
    scanNetwork: () => ipcRenderer.invoke('scan-network'),
    pingHost: (target) => ipcRenderer.invoke('ping-host', target),
    
    // SSH APIs
    sshConnect: (connection) => ipcRenderer.invoke('ssh-connect', connection),
    sshDisconnect: (connectionId) => ipcRenderer.invoke('ssh-disconnect', connectionId),
    selectSshKey: () => ipcRenderer.invoke('select-ssh-key'),
    saveSshConnection: (connection) => ipcRenderer.invoke('save-ssh-connection', connection),
    loadSshConnections: () => ipcRenderer.invoke('load-ssh-connections'),
    deleteSshConnection: (connectionId) => ipcRenderer.invoke('delete-ssh-connection', connectionId),
    
    // App info
    getAppVersion: () => ipcRenderer.invoke('get-app-version'),
    
    // Message passing
    on: (channel, callback) => {
      // Whitelist valid channels
      const validChannels = [
        'new-peer', 
        'peer-disconnect', 
        'new-message',
        'ssh-output',
        'ssh-error',
        'ssh-close',
        'ssh-ready'
      ];
      if (validChannels.includes(channel)) {
        // Strip event as it includes `sender`
        ipcRenderer.on(channel, (_, ...args) => callback(...args));
        return () => {
          ipcRenderer.removeListener(channel, callback);
        };
      }
    },
    
    // Remove all listeners for a channel
    removeAllListeners: (channel) => {
      const validChannels = [
        'new-peer', 
        'peer-disconnect', 
        'new-message',
        'ssh-output',
        'ssh-error',
        'ssh-close',
        'ssh-ready'
      ];
      if (validChannels.includes(channel)) {
        ipcRenderer.removeAllListeners(channel);
      }
    }
  }
);

// Expose the API methods to the renderer process
contextBridge.exposeInMainWorld('api', {
  // User APIs
  user: {
    getUsername: createApiMethod('GET', '/user/username', data => data.username),
    setUsername: (username) => createApiMethod('POST', '/user/username')({ username }),
  },
  
  // Peer APIs
  peers: {
    getActivePeers: createApiMethod('GET', '/peers/active'),
    getAllPeers: createApiMethod('GET', '/peers/all'),
  },
  
  // Messaging APIs
  messages: {
    sendPrivate: (peerId, content) => 
      createApiMethod('POST', `/messages/private/${peerId}`)({ content }),
    broadcast: (content) => 
      createApiMethod('POST', '/messages/broadcast')({ content }),
    sendToGroup: (groupId, content) => 
      createApiMethod('POST', `/messages/group/${groupId}`)({ content }),
    getHistory: (peerId, groupId, limit) => {
      const params = new URLSearchParams();
      if (peerId) params.append('peerId', peerId);
      if (groupId) params.append('groupId', groupId);
      if (limit) params.append('limit', limit.toString());
      return createApiMethod('GET', `/messages/history?${params.toString()}`)();
    },
    clearHistory: (peerId, groupId) => {
      const params = new URLSearchParams();
      if (peerId) params.append('peerId', peerId);
      if (groupId) params.append('groupId', groupId);
      return createApiMethod('DELETE', `/messages/clear?${params.toString()}`)();
    }
  },
  
  // Network APIs
  network: {
    getInterfaces: createApiMethod('GET', '/network/interfaces'),
    getInterfaceDetails: (interfaceName) => 
      createApiMethod('GET', `/network/interfaces/${interfaceName}`)(),
    configureInterface: (interfaceName, config) => 
      createApiMethod('POST', `/network/interfaces/${interfaceName}/config`)(config),
    scanNetwork: createApiMethod('GET', '/network/scan'),
  },
  
  // DHCP server APIs
  dhcp: {
    getStatus: createApiMethod('GET', '/dhcp/status'),
    configure: (enabled, network, serverIp) => 
      createApiMethod('POST', '/dhcp/config')({ enabled, network, serverIp }),
    getLeases: createApiMethod('GET', '/dhcp/leases'),
  },
  
  // SSH APIs
  ssh: {
    connect: (host, port, username, password, keyPath, name) => 
      createApiMethod('POST', '/ssh/connect')({ host, port, username, password, keyPath, name }),
    getConnection: (connectionId) => 
      createApiMethod('GET', `/ssh/connections/${connectionId}`)(),
    getAllConnections: createApiMethod('GET', '/ssh/connections'),
    closeConnection: (connectionId) => 
      createApiMethod('DELETE', `/ssh/connections/${connectionId}`)(),
    saveProfile: (name, host, port, username, keyPath) => 
      createApiMethod('POST', '/ssh/profiles')({ name, host, port, username, keyPath }),
    deleteProfile: (profileId) => 
      createApiMethod('DELETE', `/ssh/profiles/${profileId}`)(),
    getProfile: (profileId) => 
      createApiMethod('GET', `/ssh/profiles/${profileId}`)(),
    getAllProfiles: createApiMethod('GET', '/ssh/profiles'),
    connectFromProfile: (profileId, password) => 
      createApiMethod('POST', `/ssh/profiles/${profileId}/connect`)({ password }),
  },
  
  // Group APIs
  groups: {
    create: (groupName, peerIds) => 
      createApiMethod('POST', '/groups')({ groupName, peerIds }),
    addMember: (groupId, peerId) => 
      createApiMethod('POST', `/groups/${groupId}/members/${peerId}`)(),
    removeMember: (groupId, peerId) => 
      createApiMethod('DELETE', `/groups/${groupId}/members/${peerId}`)(),
    delete: (groupId) => 
      createApiMethod('DELETE', `/groups/${groupId}`)(),
  },
  
  // WebSocket connection
  socket: {
    connect: (callbacks) => {
      // If socket is already connected, disconnect first
      if (socket) {
        socket.disconnect();
      }
      
      // Import Socket.IO client
      const { io } = require('socket.io-client');
      
      // Create socket connection
      socket = io(process.env.REACT_APP_SOCKET_URL || 'http://localhost:5000', {
        transports: ['websocket'],
      });
      
      // Set up event handlers
      socket.on('connect', () => {
        console.log('WebSocket connected');
        if (callbacks && callbacks.onConnect) {
          callbacks.onConnect();
        }
      });
      
      socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        if (callbacks && callbacks.onDisconnect) {
          callbacks.onDisconnect();
        }
      });
      
      socket.on('error', (error) => {
        console.error('WebSocket error:', error);
        if (callbacks && callbacks.onError) {
          callbacks.onError(error);
        }
      });
      
      // Set up event handlers for specific events
      if (callbacks) {
        if (callbacks.onPeerEvent) {
          socket.on('peer_event', callbacks.onPeerEvent);
        }
        
        if (callbacks.onMessageEvent) {
          socket.on('message_event', callbacks.onMessageEvent);
        }
        
        if (callbacks.onNetworkChange) {
          socket.on('network_change', callbacks.onNetworkChange);
        }
        
        if (callbacks.onDHCPEvent) {
          socket.on('dhcp_event', callbacks.onDHCPEvent);
        }
        
        if (callbacks.onSSHEvent) {
          socket.on('ssh_event', callbacks.onSSHEvent);
        }
      }
      
      return true;
    },
    
    disconnect: () => {
      if (socket) {
        socket.disconnect();
        socket = null;
        return true;
      }
      return false;
    },
    
    isConnected: () => {
      return socket && socket.connected;
    },
  }
}); 