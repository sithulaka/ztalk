import axios from 'axios';

// Define base API URL
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Define API endpoints
export const ztalkApi = {
  // User-related endpoints
  users: {
    getUsername: () => api.get('/user/username'),
    setUsername: (username: string) => api.post('/user/username', { username }),
  },
  
  // Peer-related endpoints
  peers: {
    getActivePeers: () => api.get('/peers/active'),
    getAllPeers: () => api.get('/peers/all'),
  },
  
  // Messaging endpoints
  messages: {
    sendPrivateMessage: (peerId: string, content: string) => 
      api.post(`/messages/private/${peerId}`, { content }),
    sendBroadcastMessage: (content: string) => 
      api.post('/messages/broadcast', { content }),
    sendGroupMessage: (groupId: string, content: string) => 
      api.post(`/messages/group/${groupId}`, { content }),
    getMessageHistory: (peerId?: string, groupId?: string, limit?: number) => {
      const params = new URLSearchParams();
      if (peerId) params.append('peerId', peerId);
      if (groupId) params.append('groupId', groupId);
      if (limit) params.append('limit', limit.toString());
      return api.get(`/messages/history?${params.toString()}`);
    },
    clearMessages: (peerId?: string, groupId?: string) => {
      const params = new URLSearchParams();
      if (peerId) params.append('peerId', peerId);
      if (groupId) params.append('groupId', groupId);
      return api.delete(`/messages/clear?${params.toString()}`);
    },
  },
  
  // Network-related endpoints
  network: {
    getInterfaces: () => api.get('/network/interfaces'),
    getInterfaceDetails: (interfaceName: string) => 
      api.get(`/network/interfaces/${interfaceName}`),
    setInterfaceConfig: (interfaceName: string, config: any) => 
      api.post(`/network/interfaces/${interfaceName}/config`, config),
    scanNetwork: () => api.get('/network/scan'),
  },
  
  // DHCP server management
  dhcp: {
    getStatus: () => api.get('/dhcp/status'),
    enable: (enabled: boolean, network?: string, serverIp?: string) => 
      api.post('/dhcp/config', { enabled, network, serverIp }),
    getLeases: () => api.get('/dhcp/leases'),
  },
  
  // SSH connections
  ssh: {
    createConnection: (host: string, port: number, username: string, 
                       password?: string, keyPath?: string, name?: string) => 
      api.post('/ssh/connect', { host, port, username, password, keyPath, name }),
    getConnection: (connectionId: string) => 
      api.get(`/ssh/connections/${connectionId}`),
    getAllConnections: () => api.get('/ssh/connections'),
    closeConnection: (connectionId: string) => 
      api.delete(`/ssh/connections/${connectionId}`),
    saveProfile: (name: string, host: string, port: number, 
                 username: string, keyPath?: string) => 
      api.post('/ssh/profiles', { name, host, port, username, keyPath }),
    deleteProfile: (profileId: string) => 
      api.delete(`/ssh/profiles/${profileId}`),
    getProfile: (profileId: string) => 
      api.get(`/ssh/profiles/${profileId}`),
    getAllProfiles: () => api.get('/ssh/profiles'),
    connectFromProfile: (profileId: string, password?: string) => 
      api.post(`/ssh/profiles/${profileId}/connect`, { password }),
  },
  
  // Group management
  groups: {
    createGroup: (groupName: string, peerIds?: string[]) => 
      api.post('/groups', { groupName, peerIds }),
    addToGroup: (groupId: string, peerId: string) => 
      api.post(`/groups/${groupId}/members/${peerId}`),
    removeFromGroup: (groupId: string, peerId: string) => 
      api.delete(`/groups/${groupId}/members/${peerId}`),
    deleteGroup: (groupId: string) => 
      api.delete(`/groups/${groupId}`),
  },
};

export default ztalkApi; 