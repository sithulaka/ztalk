# ZTalk Rebuild Project

## app Purpose
- Real-time group and private messaging on local networks
- Multiple SSH connection handling 
- Automate SSH workflows (e.g., bulk server updates, script deployment) across multiple connections.
- Integrate with CI/CD pipelines (e.g., Jenkins, GitLab) for local network-triggered builds.
- Built-in tools for latency testing, bandwidth analysis, and device discovery.
- Real-time alerts for SSH connection failures or network bottlenecks.
- Encrypted file sharing (SFTP/SCP) directly via SSH channels.
- Drag-and-drop bulk transfers between local devices.
- Bridge local servers with cloud instances (AWS, Azure) via SSH tunneling.
- Zero-configuration networking
- Support for both Wi-Fi and Ethernet connections
- etc
- Embed task boards (Kanban-style) within group chats for agile workflows.
- Assign roles/permissions (e.g., admin, editor, guest) for secure collaboration.
- Generate logs of SSH activity, file transfers, and chat history for audits.


  

## Phase 1: Core Infrastructure
- [x] Define modern UI color scheme and design guidelines
- [x] make a costom backgrond dhcp to assign the ip for all connected devices
  - [x] Implement automatic device detection on local networks
  - [x] Support both Wi-Fi and Ethernet interfaces
  - [ ] Create fallback mechanisms when automatic discovery fails
- [x] Implement real-time messaging framework
  - [x] Create broadcast messaging system for group chats
  - [x] Develop private messaging between specific devices
  - [x] Add message delivery confirmation system

## Phase 2: SSH Functionality
- [x] Create SSH client manager
- [x] Create SSH connection example
- [x] Support multiple simultaneous SSH connections
- [x] Implement tabbed interface for each SSH session
- [x] Add SSH connection monitoring dashboard
- [x] Develop SSH profile system
- [x] Save SSH connection credentials securely
- [x] Add SSH tools and utilities
- [x] Add advanced SSH features
- [x] Key-based authentication for SSH

## Phase 3: User Interface Development
- [x] Remove current ui completely
- [x] Recreate the Ui well looking professional Dashboard using react ts and tailwindcss
  - [x] responsive dashboard
  - [x] Add notification system for alerts and errors
- [x] Build network management interface
  - [x] Display current network connections and status
  - [x] Allow manual IP configuration when needed
  - [x] Add network diagnostics tools
  - [x] Add light/dark/darkblue(currenet one)

## Phase 4: User Experience & Quality of Life
- [x] Create comprehensive notification system
  - [x] Desktop notifications for new messages and events
  - [x] In-app notification center
  - [x] Sound alerts (with mute option)
- [x] Implement message enhancements
  - [x] Message formatting (basic markdown)
  - [x] File sharing capabilities
  - [x] Read receipts
- [x] Add application settings
  - [x] Theme customization
  - [x] Application behavior preferences
  - [x] Keyboard shortcuts

## Phase 5: Cross-Platform Testing
- [x] Test on Linux distributions
  - [x] Ubuntu 20.04+
  - [x] Debian 10+
  - [x] Fedora 32+
  - [x] Arch Linux
  - [x] Kali Linux
- [x] Test on Windows 10/11
  - [x] Add Windows-specific compatibility
  - [x] Fix Windows networking issues
  - [x] Optimize UI for Windows
  - [x] Add firewall configuration for Windows

## Phase 6: Deployment and Packaging
- [x] Create automated build script
- [x] Create package for Linux distributions
- [x] Create Windows installer
  - [x] Implement portable version
  - [x] Create installer with NSIS
  - [x] Add desktop and Start Menu shortcuts

## Phase 7: Examples and Demonstrations
- [x] Create basic chat example
- [x] Create SSH connection example
- [x] Create multiple SSH connections example
- [x] Create comprehensive demo combining all functionality
- [ ] Create tutorial videos plan
- [x] Create example network configuration guide

## Phase 8: Advanced Feature Implementation
- [ ] Implement task boards for agile workflows
  - [ ] Create Kanban-style boards
  - [ ] Allow task assignment to peers
  - [ ] Add task status tracking
- [ ] Build CI/CD pipeline integration
  - [ ] Support Jenkins integration
  - [ ] Support GitLab CI/CD
  - [ ] Enable triggering remote builds
- [ ] Add security enhancements
  - [ ] End-to-end encryption for messages
  - [ ] Key-based authentication for SSH
  - [ ] Role-based access control

## Phase 9: Mobile Companion App
- [ ] Design mobile UI for iOS and Android
- [ ] Implement core messaging features for mobile
- [ ] Add SSH session monitoring for mobile
- [ ] Create alert system for mobile clients