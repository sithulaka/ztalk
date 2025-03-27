import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { NetworkProvider } from './contexts/NetworkContext';
import { SSHProvider } from './contexts/SSHContext';

// Import pages
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import SSH from './pages/SSH';
import Settings from './pages/Settings';
import NetworkTools from './pages/NetworkTools';
import NotFound from './pages/NotFound';

const App: React.FC = () => {
  return (
    <NetworkProvider>
      <SSHProvider>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-200">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/ssh" element={<SSH />} />
            <Route path="/network-tools" element={<NetworkTools />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </div>
      </SSHProvider>
    </NetworkProvider>
  );
};

export default App; 