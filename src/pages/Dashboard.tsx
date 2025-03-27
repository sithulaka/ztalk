import React from 'react';
import { Link } from 'react-router-dom';
import Layout from '../components/Layout';
import { useNetwork } from '../contexts/NetworkContext';
import { 
  ChatBubbleLeftRightIcon, 
  ServerIcon, 
  SignalIcon, 
  WrenchScrewdriverIcon,
  ArrowRightIcon,
  UserGroupIcon,
  BoltIcon
} from '@heroicons/react/24/outline';

const Dashboard: React.FC = () => {
  const { peers, messages, groups, isConnected } = useNetwork();
  
  // Get recent messages (last 5)
  const recentMessages = [...messages]
    .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
    .slice(0, 5);
  
  // Get online peers count
  const onlinePeersCount = peers.filter(peer => peer.isOnline).length;
  
  return (
    <Layout title="Dashboard">
      {/* Status overview */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-6">ZTalk Dashboard</h1>
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="stat-card">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-medium">Network Status</h3>
                <p className="text-2xl font-bold mt-2 mb-1">{isConnected ? 'Connected' : 'Disconnected'}</p>
              </div>
              <div className={`p-3 rounded-full ${isConnected ? 'bg-success-100 text-success-600 dark:bg-success-900 dark:text-success-300' : 'bg-danger-100 text-danger-600 dark:bg-danger-900 dark:text-danger-300'}`}>
                <SignalIcon className="h-6 w-6" />
              </div>
            </div>
            <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {isConnected ? 'Actively communicating on local network' : 'Check your network connection'}
            </div>
          </div>
          
          <div className="stat-card">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-medium">Peers</h3>
                <p className="text-2xl font-bold mt-2 mb-1">{onlinePeersCount} <span className="text-sm font-normal text-gray-500 dark:text-gray-400">/ {peers.length}</span></p>
              </div>
              <div className="p-3 rounded-full bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300">
                <UserGroupIcon className="h-6 w-6" />
              </div>
            </div>
            <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {onlinePeersCount > 0 ? `${onlinePeersCount} peers online now` : 'No peers currently online'}
            </div>
          </div>
          
          <div className="stat-card">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-medium">Messages</h3>
                <p className="text-2xl font-bold mt-2 mb-1">{messages.length}</p>
              </div>
              <div className="p-3 rounded-full bg-info-100 text-info-600 dark:bg-info-900 dark:text-info-300">
                <ChatBubbleLeftRightIcon className="h-6 w-6" />
              </div>
            </div>
            <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {messages.length > 0 ? `${messages.length} messages exchanged` : 'No messages yet'}
            </div>
          </div>
          
          <div className="stat-card">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-lg font-medium">Groups</h3>
                <p className="text-2xl font-bold mt-2 mb-1">{groups.length}</p>
              </div>
              <div className="p-3 rounded-full bg-warning-100 text-warning-600 dark:bg-warning-900 dark:text-warning-300">
                <UserGroupIcon className="h-6 w-6" />
              </div>
            </div>
            <div className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {groups.length > 0 ? `${groups.length} active groups` : 'No groups created yet'}
            </div>
          </div>
        </div>
      </div>
      
      {/* Quick actions */}
      <div className="mb-6">
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link to="/chat" className="quick-action-card">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-medium">Start Messaging</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Chat with peers on your network
                </p>
              </div>
              <div className="icon-container bg-primary-100 text-primary-600 dark:bg-primary-900 dark:text-primary-300">
                <ChatBubbleLeftRightIcon className="h-6 w-6" />
              </div>
            </div>
          </Link>
          
          <Link to="/ssh" className="quick-action-card">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-medium">SSH Connections</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Manage and connect to remote servers
                </p>
              </div>
              <div className="icon-container bg-info-100 text-info-600 dark:bg-info-900 dark:text-info-300">
                <ServerIcon className="h-6 w-6" />
              </div>
            </div>
          </Link>
          
          <Link to="/network" className="quick-action-card">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-medium">Network Tools</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Diagnose and configure your network
                </p>
              </div>
              <div className="icon-container bg-warning-100 text-warning-600 dark:bg-warning-900 dark:text-warning-300">
                <WrenchScrewdriverIcon className="h-6 w-6" />
              </div>
            </div>
          </Link>
        </div>
      </div>
      
      {/* Recent activities */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recent messages */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Recent Messages</h2>
            <Link to="/chat" className="text-primary-600 dark:text-primary-400 hover:underline text-sm flex items-center">
              View all <ArrowRightIcon className="h-4 w-4 ml-1" />
            </Link>
          </div>
          
          {recentMessages.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <ChatBubbleLeftRightIcon className="h-12 w-12 mx-auto mb-3 opacity-20" />
              <p>No messages yet</p>
              <Link to="/chat" className="text-primary-600 dark:text-primary-400 hover:underline text-sm block mt-2">
                Start a conversation
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {recentMessages.map(msg => (
                <div key={msg.id} className="border-b border-gray-100 dark:border-gray-700 pb-3 last:border-0">
                  <div className="flex justify-between mb-1">
                    <span className="font-medium">
                      {msg.sender === 'self' ? 'You' : msg.senderName}
                      {msg.recipient && msg.recipient !== 'self' && ' → ' + (peers.find(p => p.id === msg.recipient)?.name || 'Unknown')}
                      {msg.recipient === 'self' && ' → You'}
                      {msg.group && ' → ' + (groups.find(g => g.id === msg.group)?.name || 'Group')}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-1">
                    {msg.content}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {/* Network status */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Network Status</h2>
            <Link to="/network" className="text-primary-600 dark:text-primary-400 hover:underline text-sm flex items-center">
              Network tools <ArrowRightIcon className="h-4 w-4 ml-1" />
            </Link>
          </div>
          
          <div className="space-y-6">
            {/* Connected peers */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Connected Peers</h3>
              {peers.length === 0 ? (
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  No peers discovered yet
                </div>
              ) : (
                <div className="space-y-2">
                  {peers.map(peer => (
                    <div key={peer.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                      <div className="flex items-center">
                        <div className={`h-2 w-2 rounded-full ${peer.isOnline ? 'bg-success-500' : 'bg-gray-300 dark:bg-gray-600'} mr-3`}></div>
                        <span className="font-medium">{peer.name}</span>
                      </div>
                      <Link to="/chat" className="text-primary-600 dark:text-primary-400 hover:underline text-xs">
                        Message
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* Quick Stats */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">Activity</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                  <div className="text-sm text-gray-500 dark:text-gray-400">Messages Today</div>
                  <div className="text-xl font-medium mt-1">
                    {messages.filter(m => 
                      m.timestamp.toDateString() === new Date().toDateString()
                    ).length}
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3">
                  <div className="text-sm text-gray-500 dark:text-gray-400">Active Groups</div>
                  <div className="text-xl font-medium mt-1">{groups.length}</div>
                </div>
              </div>
            </div>
            
            {/* Tips */}
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-100 dark:border-blue-800">
              <div className="flex">
                <div className="p-2 bg-blue-100 dark:bg-blue-800 rounded-full mr-3">
                  <BoltIcon className="h-5 w-5 text-blue-600 dark:text-blue-300" />
                </div>
                <div>
                  <h3 className="font-medium text-blue-800 dark:text-blue-300">Pro Tip</h3>
                  <p className="text-sm text-blue-700 dark:text-blue-400 mt-1">
                    Use network tools to diagnose connectivity issues with peers or scan your local network for devices.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;