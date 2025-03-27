import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { toast } from 'react-toastify';

// SSH Connection types
export interface SSHConfig {
  id?: string;
  name: string;
  host: string;
  port: number;
  username: string;
  password?: string;
  privateKey?: string;
  passphrase?: string;
  savePassword: boolean;
}

export interface SSHConnection {
  id: string;
  config: SSHConfig;
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  error?: string;
  lastActivity: Date;
  history: {
    command: string;
    timestamp: Date;
  }[];
}

export interface SSHOutput {
  connectionId: string;
  output: string;
  error: boolean;
  timestamp: Date;
}

// Define the context type
interface SSHContextType {
  connections: SSHConnection[];
  outputs: Record<string, SSHOutput[]>;
  savedConfigs: SSHConfig[];
  activeConnection: string | null;
  isConnecting: boolean;
  connect: (config: SSHConfig) => Promise<string | null>;
  disconnect: (connectionId: string) => Promise<boolean>;
  executeCommand: (connectionId: string, command: string) => Promise<boolean>;
  setActiveConnection: (connectionId: string | null) => void;
  saveConfig: (config: SSHConfig) => void;
  deleteConfig: (configId: string) => void;
  clearOutput: (connectionId: string) => void;
  uploadFile: (connectionId: string, localPath: string, remotePath: string) => Promise<boolean>;
  downloadFile: (connectionId: string, remotePath: string, localPath: string) => Promise<boolean>;
}

// Create the context
const SSHContext = createContext<SSHContextType | undefined>(undefined);

// Provider component
export const SSHProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [connections, setConnections] = useState<SSHConnection[]>([]);
  const [outputs, setOutputs] = useState<Record<string, SSHOutput[]>>({});
  const [savedConfigs, setSavedConfigs] = useState<SSHConfig[]>([]);
  const [activeConnection, setActiveConnection] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState<boolean>(false);

  // Load saved SSH configs from localStorage on mount
  useEffect(() => {
    const savedSSHConfigs = localStorage.getItem('ssh-configs');
    if (savedSSHConfigs) {
      try {
        const parsedConfigs = JSON.parse(savedSSHConfigs);
        setSavedConfigs(parsedConfigs);
      } catch (error) {
        console.error('Failed to parse saved SSH configs:', error);
        // If parsing fails, reset saved configs
        localStorage.removeItem('ssh-configs');
      }
    }
    
    // Set up event listeners for SSH output
    if (typeof window !== 'undefined' && 'electron' in window) {
      window.electron.on('ssh-output', (output: SSHOutput) => {
        setOutputs(prev => {
          const connectionOutputs = prev[output.connectionId] || [];
          return {
            ...prev,
            [output.connectionId]: [...connectionOutputs, output]
          };
        });
      });
    }
    
    return () => {
      if (typeof window !== 'undefined' && 'electron' in window) {
        window.electron.removeAllListeners('ssh-output');
      }
    };
  }, []);

  // Save configs to localStorage when they change
  useEffect(() => {
    localStorage.setItem('ssh-configs', JSON.stringify(savedConfigs));
  }, [savedConfigs]);

  // Connect to SSH server
  const connect = useCallback(async (config: SSHConfig): Promise<string | null> => {
    setIsConnecting(true);
    
    try {
      // Generate a unique ID for this connection
      const connectionId = config.id || `conn-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      
      // In actual implementation, call Electron's connectSSH
      // For now, simulate connection
      
      // Create a new connection object
      const newConnection: SSHConnection = {
        id: connectionId,
        config: {
          ...config,
          // Remove password if not to be saved
          password: config.savePassword ? config.password : undefined,
        },
        status: 'connecting',
        lastActivity: new Date(),
        history: []
      };
      
      // Add to connections list
      setConnections(prev => [...prev, newConnection]);
      
      // Initialize outputs for this connection
      setOutputs(prev => ({
        ...prev,
        [connectionId]: [{
          connectionId,
          output: `Connecting to ${config.host}:${config.port} as ${config.username}...\r\n`,
          error: false,
          timestamp: new Date()
        }]
      }));
      
      // Simulate connection process
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Update connection status to connected
      setConnections(prev => prev.map(conn => 
        conn.id === connectionId 
          ? { ...conn, status: 'connected' } 
          : conn
      ));
      
      // Add connection success message
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: `Connected to ${config.host}\r\n`,
            error: false,
            timestamp: new Date()
          }]
        };
      });
      
      // Set this as the active connection if there isn't one already
      if (!activeConnection) {
        setActiveConnection(connectionId);
      }
      
      toast.success(`Connected to ${config.host}`);
      setIsConnecting(false);
      return connectionId;
      
    } catch (error) {
      console.error('SSH connection error:', error);
      toast.error(`Failed to connect: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setIsConnecting(false);
      return null;
    }
  }, [activeConnection]);

  // Disconnect from SSH server
  const disconnect = useCallback(async (connectionId: string): Promise<boolean> => {
    try {
      // In actual implementation, call Electron's disconnectSSH
      // For now, simulate disconnection
      
      // Update connection status
      setConnections(prev => prev.map(conn => 
        conn.id === connectionId 
          ? { ...conn, status: 'disconnected' } 
          : conn
      ));
      
      // Add disconnection message to output
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: 'Disconnected\r\n',
            error: false,
            timestamp: new Date()
          }]
        };
      });
      
      // If this was the active connection, clear it
      if (activeConnection === connectionId) {
        setActiveConnection(null);
      }
      
      toast.info('Disconnected from SSH server');
      return true;
      
    } catch (error) {
      console.error('SSH disconnection error:', error);
      toast.error(`Failed to disconnect: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return false;
    }
  }, [activeConnection]);

  // Execute command on SSH server
  const executeCommand = useCallback(async (connectionId: string, command: string): Promise<boolean> => {
    try {
      // Find the connection
      const connection = connections.find(conn => conn.id === connectionId);
      if (!connection || connection.status !== 'connected') {
        throw new Error('Not connected');
      }
      
      // Add command to history
      setConnections(prev => prev.map(conn => 
        conn.id === connectionId 
          ? { 
              ...conn, 
              lastActivity: new Date(),
              history: [...conn.history, { command, timestamp: new Date() }]
            } 
          : conn
      ));
      
      // Add command to output
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: `$ ${command}\r\n`,
            error: false,
            timestamp: new Date()
          }]
        };
      });
      
      // In actual implementation, call Electron's executeSSHCommand
      // For now, simulate command execution
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Simulate command output
      const commandOutput = getSimulatedCommandOutput(command);
      
      // Add output to terminal
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: commandOutput,
            error: false,
            timestamp: new Date()
          }]
        };
      });
      
      return true;
      
    } catch (error) {
      console.error('SSH command execution error:', error);
      
      // Add error to output
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: `Error: ${error instanceof Error ? error.message : 'Unknown error'}\r\n`,
            error: true,
            timestamp: new Date()
          }]
        };
      });
      
      return false;
    }
  }, [connections]);

  // Helper function to simulate command output for demo purposes
  const getSimulatedCommandOutput = (command: string): string => {
    const cmd = command.trim().toLowerCase();
    
    if (cmd === 'ls' || cmd === 'ls -la') {
      return `total 32
drwxr-xr-x  5 user group  160 Jul 22 10:30 .
drwxr-xr-x 15 user group  480 Jul 22 10:25 ..
-rw-r--r--  1 user group  230 Jul 22 10:28 .gitignore
drwxr-xr-x  8 user group  256 Jul 22 10:27 node_modules
-rw-r--r--  1 user group  390 Jul 22 10:26 package.json
-rw-r--r--  1 user group 9382 Jul 22 10:26 package-lock.json
drwxr-xr-x  4 user group  128 Jul 22 10:26 public
drwxr-xr-x  5 user group  160 Jul 22 10:29 src
-rw-r--r--  1 user group  450 Jul 22 10:26 tsconfig.json\r\n`;
    }
    
    if (cmd === 'pwd') {
      return `/home/user/projects\r\n`;
    }
    
    if (cmd === 'date') {
      return `${new Date().toString()}\r\n`;
    }
    
    if (cmd === 'whoami') {
      return `user\r\n`;
    }
    
    if (cmd === 'uname -a') {
      return `Linux hostname 5.15.0-78-generic #85-Ubuntu SMP Fri Jul 7 15:26:27 UTC 2023 x86_64 GNU/Linux\r\n`;
    }
    
    if (cmd.startsWith('echo ')) {
      return `${command.substring(5)}\r\n`;
    }
    
    if (cmd === 'help' || cmd === '--help') {
      return `Available commands in demo: ls, pwd, date, whoami, uname -a, echo, help\r\n`;
    }
    
    return `Command not found: ${command}\r\n`;
  };

  // Save SSH configuration
  const saveConfig = useCallback((config: SSHConfig) => {
    const configId = config.id || `config-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // Update the config with an ID if it doesn't have one
    const updatedConfig = {
      ...config,
      id: configId
    };
    
    // Check if this is an update or a new config
    const existingIndex = savedConfigs.findIndex(c => c.id === configId);
    
    if (existingIndex >= 0) {
      // Update existing config
      setSavedConfigs(prev => [
        ...prev.slice(0, existingIndex),
        updatedConfig,
        ...prev.slice(existingIndex + 1)
      ]);
      toast.success(`Updated SSH profile: ${config.name}`);
    } else {
      // Add new config
      setSavedConfigs(prev => [...prev, updatedConfig]);
      toast.success(`Saved SSH profile: ${config.name}`);
    }
  }, [savedConfigs]);

  // Delete SSH configuration
  const deleteConfig = useCallback((configId: string) => {
    setSavedConfigs(prev => prev.filter(config => config.id !== configId));
    toast.info('SSH profile deleted');
  }, []);

  // Clear terminal output for a connection
  const clearOutput = useCallback((connectionId: string) => {
    setOutputs(prev => ({
      ...prev,
      [connectionId]: [{
        connectionId,
        output: 'Terminal cleared\r\n',
        error: false,
        timestamp: new Date()
      }]
    }));
  }, []);

  // Upload file to SSH server
  const uploadFile = useCallback(async (connectionId: string, localPath: string, remotePath: string): Promise<boolean> => {
    try {
      // Find the connection
      const connection = connections.find(conn => conn.id === connectionId);
      if (!connection || connection.status !== 'connected') {
        throw new Error('Not connected');
      }
      
      // Add message to output
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: `Uploading ${localPath} to ${remotePath}...\r\n`,
            error: false,
            timestamp: new Date()
          }]
        };
      });
      
      // In actual implementation, call Electron's uploadFile
      // For now, simulate file upload
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Add success message to output
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: `File uploaded successfully\r\n`,
            error: false,
            timestamp: new Date()
          }]
        };
      });
      
      toast.success(`File uploaded to ${connection.config.host}`);
      return true;
      
    } catch (error) {
      console.error('File upload error:', error);
      
      // Add error to output
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: `Upload error: ${error instanceof Error ? error.message : 'Unknown error'}\r\n`,
            error: true,
            timestamp: new Date()
          }]
        };
      });
      
      toast.error(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return false;
    }
  }, [connections]);

  // Download file from SSH server
  const downloadFile = useCallback(async (connectionId: string, remotePath: string, localPath: string): Promise<boolean> => {
    try {
      // Find the connection
      const connection = connections.find(conn => conn.id === connectionId);
      if (!connection || connection.status !== 'connected') {
        throw new Error('Not connected');
      }
      
      // Add message to output
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: `Downloading ${remotePath} to ${localPath}...\r\n`,
            error: false,
            timestamp: new Date()
          }]
        };
      });
      
      // In actual implementation, call Electron's downloadFile
      // For now, simulate file download
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Add success message to output
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: `File downloaded successfully\r\n`,
            error: false,
            timestamp: new Date()
          }]
        };
      });
      
      toast.success(`File downloaded from ${connection.config.host}`);
      return true;
      
    } catch (error) {
      console.error('File download error:', error);
      
      // Add error to output
      setOutputs(prev => {
        const connectionOutputs = prev[connectionId] || [];
        return {
          ...prev,
          [connectionId]: [...connectionOutputs, {
            connectionId,
            output: `Download error: ${error instanceof Error ? error.message : 'Unknown error'}\r\n`,
            error: true,
            timestamp: new Date()
          }]
        };
      });
      
      toast.error(`Download failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return false;
    }
  }, [connections]);

  // Provide the context value
  const value = {
    connections,
    outputs,
    savedConfigs,
    activeConnection,
    isConnecting,
    connect,
    disconnect,
    executeCommand,
    setActiveConnection,
    saveConfig,
    deleteConfig,
    clearOutput,
    uploadFile,
    downloadFile
  };

  return (
    <SSHContext.Provider value={value}>
      {children}
    </SSHContext.Provider>
  );
};

// Custom hook to use the SSH context
export const useSSH = (): SSHContextType => {
  const context = useContext(SSHContext);
  
  if (context === undefined) {
    throw new Error('useSSH must be used within an SSHProvider');
  }
  
  return context;
}; 