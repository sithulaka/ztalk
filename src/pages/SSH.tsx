import React, { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { toast } from 'react-toastify';
import { PlusIcon, TrashIcon, ArrowPathIcon, PlayIcon, StopIcon } from '@heroicons/react/24/outline';

interface SSHConnection {
  id: string;
  name: string;
  host: string;
  port: number;
  username: string;
  authType: 'password' | 'key';
  status: 'disconnected' | 'connected' | 'connecting' | 'error';
  lastConnected?: Date;
  error?: string;
}

const SSH: React.FC = () => {
  const [connections, setConnections] = useState<SSHConnection[]>([]);
  const [showNewForm, setShowNewForm] = useState(false);
  const [selectedConnection, setSelectedConnection] = useState<string | null>(null);
  const [activeTerminals, setActiveTerminals] = useState<Record<string, boolean>>({});
  
  // Form state
  const [newConnection, setNewConnection] = useState<Omit<SSHConnection, 'id' | 'status'>>({
    name: '',
    host: '',
    port: 22,
    username: '',
    authType: 'password'
  });
  const [password, setPassword] = useState('');
  const [keyPath, setKeyPath] = useState('');
  
  // Load connections from storage on mount
  useEffect(() => {
    // This would normally use Electron's IPC to get data from main process
    const loadedConnections: SSHConnection[] = [
      {
        id: '1',
        name: 'Development Server',
        host: '192.168.1.100',
        port: 22,
        username: 'dev',
        authType: 'key',
        status: 'disconnected',
        lastConnected: new Date(Date.now() - 86400000) // 1 day ago
      },
      {
        id: '2',
        name: 'Production Server',
        host: 'example.com',
        port: 2222,
        username: 'admin',
        authType: 'password',
        status: 'disconnected'
      }
    ];
    
    setConnections(loadedConnections);
  }, []);
  
  // Handle creating a new connection
  const handleCreateConnection = () => {
    // Validate form
    if (!newConnection.name.trim()) {
      toast.error('Please enter a connection name');
      return;
    }
    
    if (!newConnection.host.trim()) {
      toast.error('Please enter a host');
      return;
    }
    
    if (!newConnection.username.trim()) {
      toast.error('Please enter a username');
      return;
    }
    
    if (newConnection.authType === 'password' && !password) {
      toast.error('Please enter a password');
      return;
    }
    
    if (newConnection.authType === 'key' && !keyPath) {
      toast.error('Please select a key file');
      return;
    }
    
    // Generate a unique ID
    const id = Math.random().toString(36).substring(2, 9);
    
    // Add the new connection
    const connection: SSHConnection = {
      ...newConnection,
      id,
      status: 'disconnected'
    };
    
    setConnections(prev => [...prev, connection]);
    
    // Reset form
    setNewConnection({
      name: '',
      host: '',
      port: 22,
      username: '',
      authType: 'password'
    });
    setPassword('');
    setKeyPath('');
    setShowNewForm(false);
    
    toast.success(`Connection "${connection.name}" created`);
  };
  
  // Handle connecting to an SSH server
  const handleConnect = (id: string) => {
    // In a real implementation, this would use Electron's IPC to connect to the SSH server
    setConnections(prev => 
      prev.map(conn => 
        conn.id === id 
          ? { ...conn, status: 'connecting' } 
          : conn
      )
    );
    
    // Simulate connection
    setTimeout(() => {
      setConnections(prev => 
        prev.map(conn => {
          if (conn.id === id) {
            const success = Math.random() > 0.2; // 80% success rate
            
            return { 
              ...conn, 
              status: success ? 'connected' : 'error',
              lastConnected: success ? new Date() : conn.lastConnected,
              error: success ? undefined : 'Connection refused'
            };
          }
          return conn;
        })
      );
      
      const conn = connections.find(c => c.id === id);
      if (conn) {
        setActiveTerminals(prev => ({ ...prev, [id]: true }));
        toast.success(`Connected to ${conn.name}`);
      }
    }, 1500);
  };
  
  // Handle disconnecting from an SSH server
  const handleDisconnect = (id: string) => {
    setConnections(prev => 
      prev.map(conn => 
        conn.id === id 
          ? { ...conn, status: 'disconnected' } 
          : conn
      )
    );
    
    setActiveTerminals(prev => {
      const newTerminals = { ...prev };
      delete newTerminals[id];
      return newTerminals;
    });
    
    const conn = connections.find(c => c.id === id);
    if (conn) {
      toast.info(`Disconnected from ${conn.name}`);
    }
  };
  
  // Handle deleting a connection
  const handleDeleteConnection = (id: string) => {
    const conn = connections.find(c => c.id === id);
    
    if (conn?.status === 'connected') {
      toast.error('Disconnect before deleting');
      return;
    }
    
    setConnections(prev => prev.filter(conn => conn.id !== id));
    
    if (selectedConnection === id) {
      setSelectedConnection(null);
    }
    
    if (conn) {
      toast.info(`Deleted connection "${conn.name}"`);
    }
  };
  
  return (
    <Layout title="SSH">
      <div className="h-[calc(100vh-12rem)] bg-white dark:bg-gray-800 rounded-xl overflow-hidden shadow-card flex">
        {/* Sidebar with connections */}
        <div className="w-64 border-r border-gray-200 dark:border-gray-700 flex flex-col">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
            <h3 className="font-medium">Connections</h3>
            <button
              onClick={() => setShowNewForm(!showNewForm)}
              className="p-1 rounded-md text-gray-500 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
              title="Add connection"
            >
              <PlusIcon className="h-5 w-5" />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-2">
            {connections.length === 0 ? (
              <div className="text-center py-6 text-gray-500 dark:text-gray-400">
                <p>No connections yet</p>
                <button
                  onClick={() => setShowNewForm(true)}
                  className="text-primary-600 dark:text-primary-400 hover:underline mt-2"
                >
                  Add your first connection
                </button>
              </div>
            ) : (
              <div className="space-y-1">
                {connections.map(conn => (
                  <button
                    key={conn.id}
                    onClick={() => setSelectedConnection(conn.id)}
                    className={`w-full text-left px-3 py-2 rounded-md flex items-center justify-between ${
                      selectedConnection === conn.id 
                        ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300' 
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <div>
                      <div className="font-medium truncate">{conn.name}</div>
                      <div className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {conn.username}@{conn.host}:{conn.port}
                      </div>
                    </div>
                    <div className={`h-2 w-2 rounded-full ${
                      conn.status === 'connected' ? 'bg-success-500' :
                      conn.status === 'connecting' ? 'bg-warning-500' :
                      conn.status === 'error' ? 'bg-danger-500' :
                      'bg-gray-300 dark:bg-gray-600'
                    }`}></div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        
        {/* Main content area */}
        <div className="flex-1 flex flex-col">
          {showNewForm ? (
            <div className="p-4 flex-1 overflow-y-auto">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-medium">New SSH Connection</h2>
                <button
                  onClick={() => setShowNewForm(false)}
                  className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                >
                  Cancel
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Connection Name
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={newConnection.name}
                    onChange={(e) => setNewConnection(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="My Server"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Host
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={newConnection.host}
                    onChange={(e) => setNewConnection(prev => ({ ...prev, host: e.target.value }))}
                    placeholder="example.com or 192.168.1.100"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Port
                  </label>
                  <input
                    type="number"
                    className="input"
                    value={newConnection.port}
                    onChange={(e) => setNewConnection(prev => ({ ...prev, port: parseInt(e.target.value) || 22 }))}
                    min="1"
                    max="65535"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Username
                  </label>
                  <input
                    type="text"
                    className="input"
                    value={newConnection.username}
                    onChange={(e) => setNewConnection(prev => ({ ...prev, username: e.target.value }))}
                    placeholder="root"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Authentication Method
                  </label>
                  <div className="flex space-x-4">
                    <label className="flex items-center">
                      <input
                        type="radio"
                        checked={newConnection.authType === 'password'}
                        onChange={() => setNewConnection(prev => ({ ...prev, authType: 'password' }))}
                        className="mr-2"
                      />
                      Password
                    </label>
                    <label className="flex items-center">
                      <input
                        type="radio"
                        checked={newConnection.authType === 'key'}
                        onChange={() => setNewConnection(prev => ({ ...prev, authType: 'key' }))}
                        className="mr-2"
                      />
                      SSH Key
                    </label>
                  </div>
                </div>
                
                {newConnection.authType === 'password' ? (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Password
                    </label>
                    <input
                      type="password"
                      className="input"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter password"
                    />
                  </div>
                ) : (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                      SSH Key File
                    </label>
                    <div className="flex">
                      <input
                        type="text"
                        className="input rounded-r-none flex-1"
                        value={keyPath}
                        readOnly
                        placeholder="No file selected"
                      />
                      <button
                        className="btn-primary rounded-l-none"
                        onClick={() => {
                          // In a real implementation, this would use Electron's dialog to select a file
                          setKeyPath('~/.ssh/id_rsa');
                        }}
                      >
                        Browse
                      </button>
                    </div>
                  </div>
                )}
                
                <div className="pt-4">
                  <button
                    onClick={handleCreateConnection}
                    className="btn-primary"
                  >
                    Save Connection
                  </button>
                </div>
              </div>
            </div>
          ) : selectedConnection ? (
            <div className="flex-1 flex flex-col">
              {/* Connection details & actions */}
              {(() => {
                const conn = connections.find(c => c.id === selectedConnection);
                if (!conn) return null;
                
                return (
                  <>
                    <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                      <div className="flex justify-between items-center">
                        <h2 className="text-lg font-medium">{conn.name}</h2>
                        <div className="flex space-x-2">
                          {conn.status === 'connected' ? (
                            <button
                              onClick={() => handleDisconnect(conn.id)}
                              className="btn-danger"
                              title="Disconnect"
                            >
                              <StopIcon className="h-5 w-5 mr-2" />
                              Disconnect
                            </button>
                          ) : (
                            <button
                              onClick={() => handleConnect(conn.id)}
                              className="btn-success"
                              disabled={conn.status === 'connecting'}
                              title="Connect"
                            >
                              {conn.status === 'connecting' ? (
                                <>
                                  <ArrowPathIcon className="h-5 w-5 mr-2 animate-spin" />
                                  Connecting...
                                </>
                              ) : (
                                <>
                                  <PlayIcon className="h-5 w-5 mr-2" />
                                  Connect
                                </>
                              )}
                            </button>
                          )}
                          <button
                            onClick={() => handleDeleteConnection(conn.id)}
                            className="btn-outline-danger"
                            title="Delete connection"
                          >
                            <TrashIcon className="h-5 w-5" />
                          </button>
                        </div>
                      </div>
                      
                      <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Host: </span>
                          <span className="font-medium">{conn.host}:{conn.port}</span>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Username: </span>
                          <span className="font-medium">{conn.username}</span>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Authentication: </span>
                          <span className="font-medium">{conn.authType === 'password' ? 'Password' : 'SSH Key'}</span>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Status: </span>
                          <span className={`font-medium ${
                            conn.status === 'connected' ? 'text-success-600 dark:text-success-400' :
                            conn.status === 'error' ? 'text-danger-600 dark:text-danger-400' :
                            'text-gray-600 dark:text-gray-300'
                          }`}>
                            {conn.status.charAt(0).toUpperCase() + conn.status.slice(1)}
                          </span>
                        </div>
                        {conn.lastConnected && (
                          <div>
                            <span className="text-gray-500 dark:text-gray-400">Last connected: </span>
                            <span className="font-medium">{conn.lastConnected.toLocaleString()}</span>
                          </div>
                        )}
                        {conn.error && (
                          <div className="col-span-2">
                            <span className="text-gray-500 dark:text-gray-400">Error: </span>
                            <span className="font-medium text-danger-600 dark:text-danger-400">{conn.error}</span>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Terminal output */}
                    {activeTerminals[conn.id] ? (
                      <div className="flex-1 p-2 bg-gray-900 font-mono text-gray-100 overflow-auto">
                        <div className="p-2">
                          <div className="text-green-400">Connected to {conn.host} as {conn.username}</div>
                          <div className="text-gray-400">Last login: {new Date().toLocaleString()}</div>
                          <div className="mt-2">
                            <span className="text-blue-400">{conn.username}@{conn.host}:~$ </span>
                            <span className="animate-pulse">_</span>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex-1 flex items-center justify-center bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-400">
                        {conn.status === 'connecting' ? (
                          <div className="text-center">
                            <ArrowPathIcon className="h-8 w-8 mx-auto animate-spin mb-2" />
                            <p>Connecting to {conn.host}...</p>
                          </div>
                        ) : (
                          <div className="text-center">
                            <p>Not connected</p>
                            <button
                              onClick={() => handleConnect(conn.id)}
                              className="text-primary-600 dark:text-primary-400 hover:underline mt-2"
                            >
                              Connect to start a session
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500 dark:text-gray-400">
              <div className="text-center">
                <p>Select a connection or create a new one</p>
                <button
                  onClick={() => setShowNewForm(true)}
                  className="text-primary-600 dark:text-primary-400 hover:underline mt-2"
                >
                  Add a new connection
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
};

export default SSH; 