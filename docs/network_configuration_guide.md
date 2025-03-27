# ZTalk Network Configuration Guide

This guide provides detailed instructions for configuring ZTalk to work optimally on various network setups, including troubleshooting common connectivity issues.

## Network Requirements

ZTalk is designed to work on local networks with minimal configuration. However, understanding your network environment can help ensure optimal performance:

- **Local Network Connectivity**: Devices must be on the same local network
- **Multicast Support**: Network must allow multicast traffic for peer discovery
- **Port Requirements**: Default UDP port 5353 for mDNS discovery and TCP port 8080 for messaging

## Network Types

### Home Networks

Most home networks will work with ZTalk without additional configuration. These networks typically:
- Use a single router
- Provide DHCP for automatic IP assignment
- Allow multicast traffic by default

**Recommended Configuration**:
- Use default ZTalk settings
- Ensure all devices are connected to the same WiFi network or router

### Office Networks

Office networks may have additional security measures that can affect ZTalk:
- VLANs separating different departments
- Firewall rules restricting multicast
- Network policies limiting peer-to-peer traffic

**Recommended Configuration**:
- Verify all devices are on the same network segment/VLAN
- Check with network administrator about multicast permissions
- If multicast is blocked, use manual peer configuration (see below)

### Public Networks

Public networks like cafes, hotels, and airports often have limitations:
- Client isolation (prevents devices from seeing each other)
- Limited broadcast/multicast support
- Captive portals that may interfere with networking

**Recommended Configuration**:
- Public networks may not work with ZTalk's automatic discovery
- Consider creating a personal hotspot from a mobile device instead
- Use manual peer configuration when necessary

## Manual Configuration

If automatic discovery doesn't work, you can manually configure peer connections:

### Setting Static IP Addresses

To manually configure a connection:

1. Find your IP address:
   - Windows: Run `ipconfig` in Command Prompt
   - Linux: Run `ip addr` in Terminal
   - macOS: Open System Preferences > Network

2. In ZTalk, use the Network Settings to add a manual peer:
   ```
   ZTalk Demo > /mode chat
   chat> /manual_connect 192.168.1.100
   ```

3. Both peers must add each other's IP addresses for bidirectional communication

### Working with Multiple Network Interfaces

If your device has multiple network interfaces (e.g., both WiFi and Ethernet connected):

1. ZTalk will attempt to use all available interfaces by default
2. To specify a preferred interface, use the `--interface` option:
   ```
   python ztalk.py demo --interface eth0
   ```
3. You can view active interfaces within ZTalk:
   ```
   chat> /network_info
   ```

## Firewall Configuration

### Windows Firewall

1. When first running ZTalk, Windows may prompt to allow it through the firewall
2. If you need to manually add it:
   - Open Windows Defender Firewall
   - Select "Allow an app through firewall"
   - Browse to the ZTalk executable or Python interpreter
   - Ensure both "Private" and "Public" networks are checked

### Linux Firewall (ufw/iptables)

Allow necessary ports:
```bash
sudo ufw allow 5353/udp
sudo ufw allow 8080/tcp
```

### macOS Firewall

1. Open System Preferences > Security & Privacy > Firewall
2. Click "Firewall Options..."
3. Click "+" to add Python or the ZTalk application
4. Set it to "Allow incoming connections"

## Troubleshooting

### No Peers Found

If ZTalk cannot discover peers on the network:

1. **Verify Network Connectivity**
   - Confirm both devices are on the same network
   - Try pinging between the devices

2. **Check Multicast**
   - Run this test to verify multicast functionality:
   ```
   python ztalk.py demo --test-multicast
   ```

3. **Manual Connection**
   - Try manual IP connection as described above

### Intermittent Connections

If peers appear and disappear:

1. **Check for Network Interference**
   - WiFi interference from other networks
   - Power-saving modes on laptops

2. **Adjust Heartbeat Interval**
   ```
   python ztalk.py demo --heartbeat-interval 5
   ```

3. **Use Wired Connection**
   - Switch to wired Ethernet if available for more stability

### Connection Errors

If you see specific error messages:

1. **"Network unreachable"**
   - Network interface may be down or configured incorrectly
   - Check network settings and cable connections

2. **"Connection refused"**
   - Firewall may be blocking the connection
   - Verify firewall settings on both devices

3. **"Permission denied"**
   - On Linux, may need to run with elevated privileges for certain operations
   - Try `sudo python ztalk.py demo` for testing purposes

## Advanced Configurations

### Creating an Isolated Network

For maximum privacy or when no infrastructure exists:

1. **Ad-hoc WiFi Network**
   - Create a computer-to-computer network
   - Connect all devices to this network
   - No internet access, but excellent for isolated ZTalk usage

2. **Mobile Hotspot**
   - Use a smartphone to create a personal hotspot
   - Connect all ZTalk devices to this hotspot
   - Maintains internet access while providing local networking

### VPN Considerations

When connecting through VPNs:

1. ZTalk may not work across different VPN endpoints
2. For best results, ensure all devices connect to the same VPN server
3. Some VPNs block multicast traffic - check with your provider

## Network Performance Optimization

For the best ZTalk experience:

1. **Reduce Network Congestion**
   - Use 5GHz WiFi when available (less interference)
   - Consider QoS settings on your router to prioritize ZTalk traffic

2. **Optimize for Multiple SSH Connections**
   - For multiple SSH sessions, consider increasing bandwidth allocation
   - Set SSH compression for slow networks:
   ```
   chat> /mode ssh
   ssh> /connect
   ...
   Enable compression? (y/n) [n]: y
   ```

3. **Large Group Chats**
   - For networks with many ZTalk users, consider using groups instead of broadcasts
   - Limit unnecessary file transfers in congested networks

## Example Network Setups

### Home Office Setup

```
Internet ---> Router (192.168.1.1)
                 |
     +-----------+-----------+
     |           |           |
Desktop       Laptop       Mobile
(Ethernet)    (WiFi)     (WiFi)
192.168.1.10  192.168.1.20  192.168.1.30
```

All devices will discover each other automatically.

### Conference Room Setup

```
           Guest WiFi
              |
Laptop1 --- Switch --- Laptop2
 |                      |
Laptop3 --- Ethernet -- Laptop4
```

- All connected devices share the same network
- No internet access required
- Perfect for collaborative sessions

## Further Assistance

If you continue to experience network issues:

1. Enable debug logging for detailed information:
   ```
   python ztalk.py demo --debug
   ```

2. Join our community forum for support:
   ```
   https://github.com/yourusername/ztalk/discussions
   ```

3. Check for updated configurations in our online documentation 