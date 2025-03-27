const { contextBridge, ipcRenderer } = require('electron');

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