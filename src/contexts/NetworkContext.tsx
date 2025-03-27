import React, { createContext, useContext, useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { toast } from 'react-toastify';

// Types
export interface Peer {
  id: string;
  name: string;
  isOnline: boolean;
  lastSeen?: Date;
}

export interface Group {
  id: string;
  name: string;
  members: string[];
  createdAt: Date;
}

export interface Message {
  id: string;
  content: string;
  sender: string;
  senderName: string;
  recipient?: string;
  group?: string;
  timestamp: Date;
  isPrivate: boolean;
  isRead: boolean;
}

interface NetworkContextType {
  username: string;
  setUsername: (name: string) => void;
  peers: Peer[];
  messages: Message[];
  groups: Group[];
  selectedPeer: Peer | null;
  selectedGroup: Group | null;
  sendMessage: (content: string, recipientId?: string, groupId?: string) => void;
  selectPeer: (peerId: string | null) => void;
  selectGroup: (groupId: string | null) => void;
  createGroup: (name: string, memberIds: string[]) => void;
  isConnected: boolean;
}

const NetworkContext = createContext<NetworkContextType | undefined>(undefined);

export const NetworkProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [username, setUsername] = useState(() => {
    const savedUsername = localStorage.getItem('ztalk-username');
    return savedUsername || `User_${Math.floor(Math.random() * 10000)}`;
  });
  
  const [peers, setPeers] = useState<Peer[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedPeer, setSelectedPeer] = useState<Peer | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  // Save username to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('ztalk-username', username);
  }, [username]);
  
  // Initialize with mock data
  useEffect(() => {
    // Simulate discovering peers
    const mockPeers: Peer[] = [
      {
        id: '1',
        name: 'Alice',
        isOnline: true,
        lastSeen: new Date()
      },
      {
        id: '2',
        name: 'Bob',
        isOnline: true,
        lastSeen: new Date()
      },
      {
        id: '3',
        name: 'Charlie',
        isOnline: false,
        lastSeen: new Date(Date.now() - 3600000) // 1 hour ago
      }
    ];
    
    // Simulate existing groups
    const mockGroups: Group[] = [
      {
        id: 'g1',
        name: 'Team Alpha',
        members: ['1', '2', 'self'],
        createdAt: new Date(Date.now() - 86400000 * 2) // 2 days ago
      }
    ];
    
    // Simulate message history
    const mockMessages: Message[] = [
      {
        id: uuidv4(),
        content: 'Hello everyone! Welcome to the broadcast channel.',
        sender: 'self',
        senderName: username,
        timestamp: new Date(Date.now() - 3600000 * 2), // 2 hours ago
        isPrivate: false,
        isRead: true
      },
      {
        id: uuidv4(),
        content: 'Hi there! Happy to be here.',
        sender: '1',
        senderName: 'Alice',
        timestamp: new Date(Date.now() - 3600000 * 1.5), // 1.5 hours ago
        isPrivate: false,
        isRead: true
      },
      {
        id: uuidv4(),
        content: 'Hey Alice, can you help me with something?',
        sender: 'self',
        senderName: username,
        recipient: '1',
        timestamp: new Date(Date.now() - 3600000), // 1 hour ago
        isPrivate: true,
        isRead: true
      },
      {
        id: uuidv4(),
        content: 'Sure, what do you need?',
        sender: '1',
        senderName: 'Alice',
        recipient: 'self',
        timestamp: new Date(Date.now() - 3600000 + 300000), // 55 mins ago
        isPrivate: true,
        isRead: true
      },
      {
        id: uuidv4(),
        content: 'Team update: We\'re making good progress on the project.',
        sender: '1',
        senderName: 'Alice',
        group: 'g1',
        timestamp: new Date(Date.now() - 1800000), // 30 mins ago
        isPrivate: false,
        isRead: true
      }
    ];
    
    setPeers(mockPeers);
    setGroups(mockGroups);
    setMessages(mockMessages);
    setIsConnected(true);
    
    // Simulate receiving a message after a delay
    setTimeout(() => {
      const newMessage: Message = {
        id: uuidv4(),
        content: 'Hey everyone, just checking in. How\'s it going?',
        sender: '2',
        senderName: 'Bob',
        timestamp: new Date(),
        isPrivate: false,
        isRead: false
      };
      
      setMessages(prev => [...prev, newMessage]);
      toast.info(`New message from ${newMessage.senderName}`);
    }, 10000);
  }, [username]);
  
  // Select a peer by ID
  const selectPeer = (peerId: string | null) => {
    if (!peerId) {
      setSelectedPeer(null);
      return;
    }
    
    const peer = peers.find(p => p.id === peerId);
    setSelectedPeer(peer || null);
    
    // Mark messages from this peer as read
    if (peer) {
      setMessages(prev => 
        prev.map(msg => 
          (msg.sender === peer.id && msg.recipient === 'self' && !msg.isRead)
            ? { ...msg, isRead: true }
            : msg
        )
      );
    }
  };
  
  // Select a group by ID
  const selectGroup = (groupId: string | null) => {
    if (!groupId) {
      setSelectedGroup(null);
      return;
    }
    
    const group = groups.find(g => g.id === groupId);
    setSelectedGroup(group || null);
    
    // Mark group messages as read
    if (group) {
      setMessages(prev => 
        prev.map(msg => 
          (msg.group === group.id && !msg.isRead)
            ? { ...msg, isRead: true }
            : msg
        )
      );
    }
  };
  
  // Send a message to a recipient, group, or broadcast
  const sendMessage = (content: string, recipientId?: string, groupId?: string) => {
    if (!content.trim()) return;
    
    const newMessage: Message = {
      id: uuidv4(),
      content,
      sender: 'self',
      senderName: username,
      recipient: recipientId,
      group: groupId,
      timestamp: new Date(),
      isPrivate: !!recipientId,
      isRead: true
    };
    
    setMessages(prev => [...prev, newMessage]);
    
    // Simulate receiving a response
    if (recipientId) {
      const recipient = peers.find(p => p.id === recipientId);
      if (recipient && recipient.isOnline) {
        setTimeout(() => {
          const responseContent = [
            "Thank you for your message!",
            "I'll get back to you soon.",
            "Interesting point, let me think about it.",
            "That's a great idea!",
            "I'm not sure I understand, can you clarify?"
          ];
          
          const response: Message = {
            id: uuidv4(),
            content: responseContent[Math.floor(Math.random() * responseContent.length)],
            sender: recipientId,
            senderName: recipient.name,
            recipient: 'self',
            timestamp: new Date(),
            isPrivate: true,
            isRead: false
          };
          
          setMessages(prev => [...prev, response]);
          toast.info(`New message from ${response.senderName}`);
        }, 2000 + Math.random() * 3000);
      }
    }
  };
  
  // Create a new group
  const createGroup = (name: string, memberIds: string[]) => {
    if (!name.trim() || memberIds.length === 0) return;
    
    const newGroup: Group = {
      id: uuidv4(),
      name,
      members: [...memberIds, 'self'],
      createdAt: new Date()
    };
    
    setGroups(prev => [...prev, newGroup]);
    
    // Automatically select the new group
    setSelectedGroup(newGroup);
    setSelectedPeer(null);
    
    // Add a system message about group creation
    const systemMessage: Message = {
      id: uuidv4(),
      content: `Group "${name}" created with ${memberIds.length + 1} members.`,
      sender: 'system',
      senderName: 'System',
      group: newGroup.id,
      timestamp: new Date(),
      isPrivate: false,
      isRead: true
    };
    
    setMessages(prev => [...prev, systemMessage]);
    toast.success(`Group "${name}" created successfully`);
  };
  
  return (
    <NetworkContext.Provider value={{
      username,
      setUsername,
      peers,
      messages,
      groups,
      selectedPeer,
      selectedGroup,
      sendMessage,
      selectPeer,
      selectGroup,
      createGroup,
      isConnected
    }}>
      {children}
    </NetworkContext.Provider>
  );
};

export const useNetwork = () => {
  const context = useContext(NetworkContext);
  if (context === undefined) {
    throw new Error('useNetwork must be used within a NetworkProvider');
  }
  return context;
};

export default NetworkContext; 