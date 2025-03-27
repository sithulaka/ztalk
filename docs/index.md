# ZTalk Documentation

Welcome to the ZTalk documentation. This comprehensive guide will help you install, configure, and use ZTalk for real-time messaging and SSH management on local networks.

## Table of Contents

### Getting Started
- [Quick Start Guide](#quick-start-guide)
- [Installation Guide](#installation-guide)
- [Command Line Options](#command-line-options)

### User Guides
- [Chat Functionality](chat_functionality.md)
- [SSH Management](ssh_management.md)
- [Network Configuration Guide](network_configuration_guide.md)

### Reference
- [Command Reference](command_reference.md)
- [Configuration Options](configuration_options.md)
- [API Documentation](api_documentation.md)

### Development
- [Contributing Guidelines](contributing.md)
- [Architecture Overview](architecture.md)
- [Tutorial Videos Plan](tutorial_videos.md)

## Quick Start Guide

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ztalk.git
   cd ztalk
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run ZTalk:
   ```bash
   python ztalk.py demo
   ```

### Basic Usage

ZTalk starts in chat mode by default. Here are some basic commands:

- Type a message to broadcast to all peers
- Use `/help` to see available commands
- Use `/mode ssh` to switch to SSH mode
- Use `/quit` to exit

## Installation Guide

### System Requirements

- Python 3.7 or newer
- Network connectivity (Wi-Fi or Ethernet)
- Linux, Windows, or macOS

### Detailed Installation Steps

#### Linux

```bash
# Install Python if not already installed
sudo apt update
sudo apt install python3 python3-pip

# Clone the repository
git clone https://github.com/yourusername/ztalk.git
cd ztalk

# Install dependencies
pip3 install -r requirements.txt

# Run ZTalk
python3 ztalk.py demo
```

#### Windows

1. Install Python from [python.org](https://python.org)
2. Download the ZTalk repository as ZIP or use Git
3. Open Command Prompt in the ZTalk directory
4. Run:
   ```
   pip install -r requirements.txt
   python ztalk.py demo
   ```

#### macOS

```bash
# Install Python if not already installed (using Homebrew)
brew install python

# Clone the repository
git clone https://github.com/yourusername/ztalk.git
cd ztalk

# Install dependencies
pip3 install -r requirements.txt

# Run ZTalk
python3 ztalk.py demo
```

## Command Line Options

ZTalk offers various command-line options for customization:

```
Usage: python ztalk.py [component] [options]

Components:
  demo       Full application with all features
  chat       Simple chat application
  ssh        Basic SSH client
  multi-ssh  Multiple SSH connection manager

Options:
  --username NAME    Set your display name
  --debug            Enable detailed debug logging
  --interface IFACE  Use specific network interface
  --list             Show available components
```

For example:

```bash
# Start ZTalk demo with a specific username
python ztalk.py demo --username Alice

# Start the chat component with debug logging
python ztalk.py chat --debug

# Start SSH client and connect to a specific host
python ztalk.py ssh --host example.com --username admin
```

## Next Steps

- Read the [Chat Functionality](chat_functionality.md) guide to learn about messaging features
- Explore [SSH Management](ssh_management.md) for details on managing SSH connections
- Check the [Network Configuration Guide](network_configuration_guide.md) for network setup instructions
- View the [Command Reference](command_reference.md) for a complete list of available commands 