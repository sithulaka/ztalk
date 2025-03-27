// TypeScript declarations for Electron API
interface SSHOutput {
  connectionId: string;
  data: string;
  type: 'stdout' | 'stderr';
}

interface ElectronAPI {
  // Network APIs
  getNetworkInterfaces: () => Promise<any>;
  getIpConfig: (interfaceName: string) => Promise<any>;
  applyIpConfig: (config: any) => Promise<{ success: boolean }>;
  scanNetwork: () => Promise<any[]>;
  pingHost: (target: string) => Promise<any>;
  
  // SSH APIs
  sshConnect: (connection: any) => Promise<{ success: boolean }>;
  sshDisconnect: (connectionId: string) => Promise<{ success: boolean }>;
  selectSshKey: () => Promise<string | null>;
  saveSshConnection: (connection: any) => Promise<{ success: boolean, id: string }>;
  loadSshConnections: () => Promise<any[]>;
  deleteSshConnection: (connectionId: string) => Promise<{ success: boolean }>;
  
  // Event handling
  on: (channel: string, callback: (...args: any[]) => void) => void;
  removeAllListeners: (channel: string) => void;
  
  // SSH events
  onSSHOutput: (callback: (output: SSHOutput) => void) => void;
}

interface Window {
  electron: ElectronAPI;
} 