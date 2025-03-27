import React, { useState, useRef, useEffect } from 'react';
import Layout from '../components/Layout';
import { useNetwork } from '../contexts/NetworkContext';
import { toast } from 'react-toastify';
import ReactMarkdown from 'react-markdown';
import { PaperAirplaneIcon, PaperClipIcon, UserCircleIcon, UserIcon } from '@heroicons/react/24/outline';

const Chat: React.FC = () => {
  const { 
    peers, 
    messages, 
    groups, 
    selectedPeer, 
    selectedGroup, 
    sendMessage, 
    selectPeer, 
    selectGroup, 
    createGroup, 
    username, 
    setUsername 
  } = useNetwork();
  
  const [newMessage, setNewMessage] = useState('');
  const [newGroupName, setNewGroupName] = useState('');
  const [selectedPeers, setSelectedPeers] = useState<string[]>([]);
  const [showNewGroupForm, setShowNewGroupForm] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  // Filter messages for current view
  const filteredMessages = messages.filter(msg => {
    if (selectedPeer) {
      return (msg.sender === selectedPeer.id && msg.recipient === 'self') || 
             (msg.sender === 'self' && msg.recipient === selectedPeer.id);
    } else if (selectedGroup) {
      return msg.group === selectedGroup.id;
    } else {
      return !msg.isPrivate && !msg.group;
    }
  });
  
  // Handle sending a message
  const handleSendMessage = () => {
    if (!newMessage.trim() && !attachedFile) return;
    
    let content = newMessage;
    
    // Add file info to message if attached
    if (attachedFile) {
      content += `\n\n📎 [${attachedFile.name}] - ${(attachedFile.size / 1024).toFixed(2)} KB`;
      
      // In a real implementation, we would upload the file
      // and add a download link to the message
      toast.info(`File attached: ${attachedFile.name}`);
      setAttachedFile(null);
    }
    
    if (selectedPeer) {
      sendMessage(content, selectedPeer.id);
    } else if (selectedGroup) {
      sendMessage(content, undefined, selectedGroup.id);
    } else {
      sendMessage(content);
    }
    
    setNewMessage('');
  };
  
  // Handle key press in text input
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  // Handle file attachment
  const handleFileAttachment = () => {
    fileInputRef.current?.click();
  };
  
  // Handle file change
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 20 * 1024 * 1024) { // 20MB limit
        toast.error('File too large. Maximum size is 20MB.');
        return;
      }
      
      setAttachedFile(file);
      toast.success(`File ready: ${file.name}`);
    }
  };
  
  // Handle creating a new group
  const handleCreateGroup = () => {
    if (!newGroupName.trim()) {
      toast.error('Please enter a group name');
      return;
    }
    
    if (selectedPeers.length === 0) {
      toast.error('Please select at least one peer');
      return;
    }
    
    createGroup(newGroupName, selectedPeers);
    setNewGroupName('');
    setSelectedPeers([]);
    setShowNewGroupForm(false);
  };
  
  // Toggle peer selection for group creation
  const togglePeerSelection = (peerId: string) => {
    setSelectedPeers(prev => 
      prev.includes(peerId) 
        ? prev.filter(id => id !== peerId) 
        : [...prev, peerId]
    );
  };
  
  // Format time
  const formatTime = (date: Date) => {
    return new Date(date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };
  
  return (
    <Layout title="Chat">
      <div className="flex h-[calc(100vh-12rem)] bg-white dark:bg-gray-800 rounded-xl overflow-hidden shadow-card">
        {/* Sidebar with peers and groups */}
        <div className="w-64 border-r border-gray-200 dark:border-gray-700 flex flex-col">
          {/* Username input */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Your Name
            </label>
            <input
              type="text"
              className="input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your name"
            />
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-6">
            {/* Broadcast channel */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Broadcast</h3>
              <button
                onClick={() => { selectPeer(null); selectGroup(null); }}
                className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                  !selectedPeer && !selectedGroup 
                    ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300' 
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                <UserCircleIcon className="h-5 w-5 mr-2" />
                <span>Everyone</span>
              </button>
            </div>
            
            {/* Peers */}
            <div>
              <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Direct Messages</h3>
              <div className="space-y-1">
                {peers.map(peer => (
                  <button
                    key={peer.id}
                    onClick={() => { selectPeer(peer.id); selectGroup(null); }}
                    className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                      selectedPeer?.id === peer.id 
                        ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300' 
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <UserIcon className="h-5 w-5 mr-2" />
                    <span className="truncate">{peer.name}</span>
                    <span className={`ml-auto h-2 w-2 rounded-full ${peer.isOnline ? 'bg-success-500' : 'bg-gray-300 dark:bg-gray-600'}`}></span>
                  </button>
                ))}
              </div>
            </div>
            
            {/* Groups */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">Groups</h3>
                <button
                  onClick={() => setShowNewGroupForm(!showNewGroupForm)}
                  className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                >
                  {showNewGroupForm ? 'Cancel' : '+ New Group'}
                </button>
              </div>
              
              {showNewGroupForm && (
                <div className="mb-3 p-3 bg-gray-50 dark:bg-gray-700 rounded-md space-y-3">
                  <input
                    type="text"
                    className="input text-sm"
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                    placeholder="Group name"
                  />
                  
                  <div className="max-h-32 overflow-y-auto">
                    {peers.map(peer => (
                      <div key={peer.id} className="flex items-center py-1">
                        <input
                          type="checkbox"
                          id={`peer-${peer.id}`}
                          checked={selectedPeers.includes(peer.id)}
                          onChange={() => togglePeerSelection(peer.id)}
                          className="mr-2"
                        />
                        <label htmlFor={`peer-${peer.id}`} className="text-sm text-gray-700 dark:text-gray-300">
                          {peer.name}
                        </label>
                      </div>
                    ))}
                  </div>
                  
                  <button
                    onClick={handleCreateGroup}
                    className="w-full btn-primary py-1 text-sm"
                  >
                    Create Group
                  </button>
                </div>
              )}
              
              <div className="space-y-1">
                {groups.map(group => (
                  <button
                    key={group.id}
                    onClick={() => { selectGroup(group.id); selectPeer(null); }}
                    className={`w-full flex items-center px-3 py-2 text-sm rounded-md ${
                      selectedGroup?.id === group.id 
                        ? 'bg-primary-100 text-primary-700 dark:bg-primary-900 dark:text-primary-300' 
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <span className="truncate">{group.name}</span>
                    <span className="ml-auto text-xs text-gray-500 dark:text-gray-400">
                      {group.members.length} members
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
        
        {/* Chat area */}
        <div className="flex-1 flex flex-col">
          {/* Chat header */}
          <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center">
            <h2 className="text-lg font-medium">
              {selectedPeer ? selectedPeer.name : selectedGroup ? selectedGroup.name : 'Broadcast Channel'}
            </h2>
            {selectedPeer && (
              <span className={`ml-2 h-2 w-2 rounded-full ${selectedPeer.isOnline ? 'bg-success-500' : 'bg-gray-300 dark:bg-gray-600'}`}></span>
            )}
            <span className="ml-auto text-sm text-gray-500 dark:text-gray-400">
              {filteredMessages.length} messages
            </span>
          </div>
          
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {filteredMessages.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <p className="text-gray-500 dark:text-gray-400">No messages yet. Start a conversation!</p>
              </div>
            ) : (
              filteredMessages.map(msg => (
                <div 
                  key={msg.id} 
                  className={`flex ${msg.sender === 'self' ? 'justify-end' : 'justify-start'}`}
                >
                  <div 
                    className={`max-w-md rounded-lg px-4 py-2 ${
                      msg.sender === 'self' 
                        ? 'bg-primary-100 text-primary-900 dark:bg-primary-900 dark:text-primary-100' 
                        : 'bg-gray-100 text-gray-900 dark:bg-gray-700 dark:text-gray-100'
                    }`}
                  >
                    {msg.sender !== 'self' && !selectedPeer && (
                      <div className="text-xs font-medium mb-1">{msg.senderName}</div>
                    )}
                    <div className="prose dark:prose-invert prose-sm max-w-none">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 text-right mt-1">
                      {formatTime(msg.timestamp)}
                    </div>
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Message input */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center">
              <button
                onClick={handleFileAttachment}
                className="p-2 rounded-full text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 mr-2"
                title="Attach file"
              >
                <PaperClipIcon className="h-5 w-5" />
              </button>
              
              <div className="flex-1 relative">
                <textarea
                  className="input py-2 min-h-[40px] max-h-32 resize-none"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder={`Message ${
                    selectedPeer ? selectedPeer.name : selectedGroup ? selectedGroup.name : 'everyone'
                  }...`}
                  rows={1}
                />
                {attachedFile && (
                  <div className="mt-2 flex items-center text-sm text-gray-600 dark:text-gray-300">
                    <PaperClipIcon className="h-4 w-4 mr-1" />
                    <span className="truncate">{attachedFile.name}</span>
                    <button
                      onClick={() => setAttachedFile(null)}
                      className="ml-2 text-gray-500 dark:text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    >
                      &times;
                    </button>
                  </div>
                )}
              </div>
              
              <button
                onClick={handleSendMessage}
                className="p-2 rounded-full bg-primary-500 text-white hover:bg-primary-600 ml-2"
                title="Send message"
              >
                <PaperAirplaneIcon className="h-5 w-5" />
              </button>
            </div>
            
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
            />
            
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              Supports Markdown formatting. Press Enter to send, Shift+Enter for a new line.
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Chat; 