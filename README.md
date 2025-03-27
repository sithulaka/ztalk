# ZTalk

ZTalk is a modern zero-configuration messaging and SSH management application for local networks.

![ZTalk Dashboard](https://via.placeholder.com/800x450/3B82F6/FFFFFF?text=ZTalk+Dashboard)

## Features

- **Zero-Configuration Networking:** Automatically discovers peers on the local network without any setup.
- **Real-time Messaging:** Chat with peers on your network with support for private, group, and broadcast messages.
- **Markdown Message Formatting:** Format your messages with Markdown including bold, italic, code blocks, and more.
- **File Sharing:** Share files with peers directly through the chat interface.
- **SSH Connection Management:** Manage multiple SSH connections with a user-friendly interface.
- **SSH Profile System:** Save SSH connection credentials securely for quick access.
- **Network Diagnostics Tools:** Scan your network, perform latency tests, and manage IP configurations.
- **Modern User Interface:** Clean, responsive design with light and dark modes.

## Installation

### Prerequisites

- Node.js (v14 or newer)
- npm or yarn

### Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ztalk.git
   cd ztalk
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run electron:start
   ```

### Building for Production

```bash
npm run electron:build
```

This will create platform-specific installers in the `dist` directory.

## Usage

### Chat Functionality

- **Broadcast Messages:** Send messages to all connected peers.
- **Private Messages:** Select a peer from the sidebar to start a private conversation.
- **Group Chats:** Create groups and add peers for collaborative discussions.
- **Message Formatting:** Use Markdown to format your messages.
- **File Sharing:** Attach files to your messages using the paper clip icon.

### SSH Functionality

- **Manage Connections:** Create, edit, and delete SSH connection profiles.
- **Quick Connect:** Connect to saved profiles with a single click.
- **Interactive Terminal:** Use the full-featured terminal for remote command execution.
- **Connection Monitoring:** View connection status and details for all your SSH sessions.

### Network Tools

- **Network Scanning:** Discover devices on your local network.
- **Latency Testing:** Test connection speed to specific hosts.
- **IP Configuration:** View and modify network interface settings.
- **Interface Monitoring:** Monitor network traffic and status for each interface.

## Architecture

ZTalk is built with modern web technologies:

- **Frontend:** React, TypeScript, TailwindCSS
- **Backend:** Electron, Node.js
- **Networking:** socket.io, bonjour-service
- **SSH:** ssh2
- **UI Components:** Heroicons, React Router

## Project Status

### Implemented Features
- ✅ Modern UI with responsive dashboard
- ✅ Real-time messaging (broadcast, private, group)
- ✅ Message formatting with Markdown
- ✅ File sharing in messages
- ✅ SSH connection management
- ✅ SSH terminal interface
- ✅ Network diagnostics tools
- ✅ IP configuration interface
- ✅ Light/dark mode support
- ✅ Notification system

### Planned Features
- ⏳ Advanced SSH features (file transfer, command history)
- ⏳ CI/CD pipeline integration
- ⏳ Task boards for agile workflows
- ⏳ End-to-end encryption for messages
- ⏳ Mobile companion app

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Frequently Asked Questions

### What should I do if I can't connect to the network?
First, ensure your network connections are working properly. Check that you're on the same local network as your peers. If problems persist, try restarting the application or using the Network Tools to diagnose connectivity issues.

### How do I send a message to another user?
Select the user from the Direct Messages list in the sidebar on the Chat page. This will open a private conversation where you can exchange messages only visible to you and the recipient.

### Can I format my messages?
Yes! ZTalk supports Markdown formatting. You can use **bold**, *italic*, `code`, and other Markdown syntax in your messages.

### How do I create a group chat?
In the Chat page, click the "+ New Group" button in the Groups section of the sidebar. Enter a name for your group and select the peers you want to include, then click "Create Group".

### Is my SSH password stored securely?
ZTalk only stores SSH connection details in memory during your session. For added security, we recommend using key-based authentication instead of passwords.

### How can I contribute to the project?
See the Contributing section above. We welcome code contributions, bug reports, and feature suggestions!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 