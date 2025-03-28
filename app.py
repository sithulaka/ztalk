#!/usr/bin/env python3
"""
ZTalk API Server

Provides a REST API and WebSocket server to connect the ZTalk backend with the React frontend.
"""

import os
import sys
import logging
import uuid
import json
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import ZTalk core
from core import ZTalkApp, Message, ZTalkPeer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('ztalk-api')

# Create Flask app
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Configure Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

# Global app instance
ztalk_app: Optional[ZTalkApp] = None

# Initialize ZTalk application
def init_ztalk_app():
    global ztalk_app
    
    try:
        logger.info("Initializing ZTalk application")
        ztalk_app = ZTalkApp()
        
        # Register event handlers
        ztalk_app.add_peer_listener(on_peer_event)
        ztalk_app.add_message_listener(on_message_event)
        ztalk_app.add_network_listener(on_network_change)
        
        # Start the application
        if not ztalk_app.start():
            logger.error("Failed to start ZTalk application")
            return False
            
        logger.info("ZTalk application started successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing ZTalk application: {e}")
        return False

# Event handlers that forward events to WebSocket clients
def on_peer_event(event_type: str, peer: ZTalkPeer):
    """Handle peer discovery events"""
    try:
        socketio.emit('peer_event', {
            'event': event_type,
            'peerId': peer.peer_id,
            'name': peer.name,
            'ipAddress': peer.ip_address,
            'timestamp': peer.last_seen
        })
    except Exception as e:
        logger.error(f"Error in peer event handler: {e}")

def on_message_event(message: Message):
    """Handle incoming messages"""
    try:
        event_data = {
            'messageId': message.message_id,
            'type': message.message_type.name.lower(),
            'content': message.content,
            'senderId': message.sender_id,
            'senderName': message.sender_name,
            'timestamp': message.timestamp
        }
        
        # Add recipient or group ID if appropriate
        if message.recipient_id:
            event_data['recipientId'] = message.recipient_id
        if message.group_id:
            event_data['groupId'] = message.group_id
            
        socketio.emit('message_event', event_data)
    except Exception as e:
        logger.error(f"Error in message event handler: {e}")

def on_network_change(new_interfaces: Dict[str, str], old_interfaces: Dict[str, str]):
    """Handle network interface changes"""
    try:
        # Process interface changes
        for name, ip in new_interfaces.items():
            if name not in old_interfaces:
                # New interface
                socketio.emit('network_change', {
                    'event': 'added',
                    'interfaceName': name,
                    'newIp': ip
                })
            elif old_interfaces[name] != ip:
                # Changed IP
                socketio.emit('network_change', {
                    'event': 'changed',
                    'interfaceName': name,
                    'oldIp': old_interfaces[name],
                    'newIp': ip
                })
                
        # Check for removed interfaces
        for name, ip in old_interfaces.items():
            if name not in new_interfaces:
                socketio.emit('network_change', {
                    'event': 'removed',
                    'interfaceName': name,
                    'oldIp': ip
                })
    except Exception as e:
        logger.error(f"Error in network change handler: {e}")

# API Routes

# User endpoints
@app.route('/api/user/username', methods=['GET'])
def get_username():
    """Get the current username"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    return jsonify({'username': ztalk_app.username})

@app.route('/api/user/username', methods=['POST'])
def set_username():
    """Set the username"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
        
    success = ztalk_app.set_username(username)
    
    if success:
        return jsonify({'username': username, 'success': True})
    else:
        return jsonify({'error': 'Failed to set username'}), 400

# Peer endpoints
@app.route('/api/peers/active', methods=['GET'])
def get_active_peers():
    """Get active peers"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    active_peers = ztalk_app.get_active_peers()
    peers_data = [{
        'peerId': peer.peer_id,
        'name': peer.name,
        'ipAddress': peer.ip_address,
        'lastSeen': peer.last_seen
    } for peer in active_peers]
    
    return jsonify(peers_data)

@app.route('/api/peers/all', methods=['GET'])
def get_all_peers():
    """Get all peers (active and inactive)"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    all_peers = ztalk_app.get_peers()
    peers_data = [{
        'peerId': peer.peer_id,
        'name': peer.name,
        'ipAddress': peer.ip_address,
        'lastSeen': peer.last_seen,
        'isActive': peer.is_active()
    } for peer in all_peers]
    
    return jsonify(peers_data)

# Messaging endpoints
@app.route('/api/messages/private/<peer_id>', methods=['POST'])
def send_private_message(peer_id):
    """Send a private message to a peer"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
        
    message_id = ztalk_app.send_message(content=content, peer_id=peer_id)
    
    if message_id:
        return jsonify({'messageId': message_id, 'success': True})
    else:
        return jsonify({'error': 'Failed to send message'}), 400

@app.route('/api/messages/broadcast', methods=['POST'])
def send_broadcast_message():
    """Send a broadcast message to all peers"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
        
    message_id = ztalk_app.broadcast_message(content=content)
    
    if message_id:
        return jsonify({'messageId': message_id, 'success': True})
    else:
        return jsonify({'error': 'Failed to send broadcast message'}), 400

@app.route('/api/messages/group/<group_id>', methods=['POST'])
def send_group_message(group_id):
    """Send a message to a group"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return jsonify({'error': 'Message content is required'}), 400
        
    message_id = ztalk_app.send_message(content=content, group_id=group_id)
    
    if message_id:
        return jsonify({'messageId': message_id, 'success': True})
    else:
        return jsonify({'error': 'Failed to send group message'}), 400

@app.route('/api/messages/history', methods=['GET'])
def get_message_history():
    """Get message history"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    peer_id = request.args.get('peerId')
    group_id = request.args.get('groupId')
    limit = request.args.get('limit', 50, type=int)
    
    messages = ztalk_app.get_messages(peer_id=peer_id, group_id=group_id, limit=limit)
    
    messages_data = [{
        'messageId': msg.message_id,
        'type': msg.message_type.name.lower(),
        'content': msg.content,
        'senderId': msg.sender_id,
        'senderName': msg.sender_name,
        'recipientId': msg.recipient_id,
        'groupId': msg.group_id,
        'timestamp': msg.timestamp
    } for msg in messages]
    
    return jsonify(messages_data)

@app.route('/api/messages/clear', methods=['DELETE'])
def clear_messages():
    """Clear message history"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    peer_id = request.args.get('peerId')
    group_id = request.args.get('groupId')
    
    success = ztalk_app.clear_messages(peer_id=peer_id, group_id=group_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to clear messages'}), 400

# Network endpoints
@app.route('/api/network/interfaces', methods=['GET'])
def get_interfaces():
    """Get active network interfaces"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    if not ztalk_app.network_manager:
        return jsonify({'error': 'Network manager not initialized'}), 500
        
    interfaces = ztalk_app.network_manager.active_interfaces
    
    return jsonify(interfaces)

@app.route('/api/network/interfaces/<interface_name>', methods=['GET'])
def get_interface_details(interface_name):
    """Get details for a specific interface"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    if not ztalk_app.network_manager:
        return jsonify({'error': 'Network manager not initialized'}), 500
        
    if interface_name not in ztalk_app.network_manager.active_interfaces:
        return jsonify({'error': 'Interface not found'}), 404
        
    # Get interface IP
    ip_address = ztalk_app.network_manager.active_interfaces.get(interface_name)
    
    # Get additional details if available
    details = {
        'name': interface_name,
        'ipAddress': ip_address,
        # Additional details would come from platform-specific calls
        # which would be implemented in the NetworkManager class
    }
    
    return jsonify(details)

@app.route('/api/network/interfaces/<interface_name>/config', methods=['POST'])
def set_interface_config(interface_name):
    """Set configuration for a specific interface"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    if not ztalk_app.network_manager:
        return jsonify({'error': 'Network manager not initialized'}), 500
        
    if interface_name not in ztalk_app.network_manager.active_interfaces:
        return jsonify({'error': 'Interface not found'}), 404
        
    # This would call methods on the network_manager to configure the interface
    # For now, we'll just return a stub response
    return jsonify({'success': True, 'message': 'Interface configuration not implemented yet'})

@app.route('/api/network/scan', methods=['GET'])
def scan_network():
    """Scan the network for devices"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    # This would call methods to perform a network scan
    # For now, we'll just return a stub response with the current peers
    peers = ztalk_app.get_active_peers()
    devices = [{
        'ipAddress': peer.ip_address,
        'name': peer.name,
        'type': 'ztalk-peer'
    } for peer in peers]
    
    return jsonify(devices)

# DHCP server endpoints
@app.route('/api/dhcp/status', methods=['GET'])
def get_dhcp_status():
    """Get DHCP server status"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    status = ztalk_app.get_dhcp_status()
    return jsonify(status)

@app.route('/api/dhcp/config', methods=['POST'])
def configure_dhcp():
    """Configure DHCP server"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    data = request.get_json()
    enabled = data.get('enabled', False)
    network = data.get('network')
    server_ip = data.get('serverIp')
    
    success = ztalk_app.enable_dhcp(enabled, network, server_ip)
    
    if success:
        return jsonify({'success': True, 'enabled': enabled})
    else:
        return jsonify({'error': 'Failed to configure DHCP server'}), 400

@app.route('/api/dhcp/leases', methods=['GET'])
def get_dhcp_leases():
    """Get DHCP leases"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    status = ztalk_app.get_dhcp_status()
    leases = status.get('leases', {})
    
    return jsonify(leases)

# SSH endpoints
@app.route('/api/ssh/connect', methods=['POST'])
def create_ssh_connection():
    """Create a new SSH connection"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    data = request.get_json()
    host = data.get('host')
    port = data.get('port', 22)
    username = data.get('username', '')
    password = data.get('password')
    key_path = data.get('keyPath')
    name = data.get('name')
    
    if not host:
        return jsonify({'error': 'Host is required'}), 400
        
    connection_id = ztalk_app.create_ssh_connection(
        host=host,
        port=port,
        username=username,
        password=password,
        key_path=key_path,
        name=name
    )
    
    if connection_id:
        return jsonify({'connectionId': connection_id, 'success': True})
    else:
        return jsonify({'error': 'Failed to create SSH connection'}), 400

@app.route('/api/ssh/connections/<connection_id>', methods=['GET'])
def get_ssh_connection(connection_id):
    """Get a specific SSH connection"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    connection = ztalk_app.get_ssh_connection(connection_id)
    
    if connection:
        return jsonify({
            'connectionId': connection.connection_id,
            'name': connection.name,
            'host': connection.host,
            'port': connection.port,
            'username': connection.username,
            'status': connection.status.name.lower()
        })
    else:
        return jsonify({'error': 'Connection not found'}), 404

@app.route('/api/ssh/connections', methods=['GET'])
def get_all_ssh_connections():
    """Get all SSH connections"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    connections = ztalk_app.get_all_ssh_connections()
    
    connections_data = [{
        'connectionId': conn.connection_id,
        'name': conn.name,
        'host': conn.host,
        'port': conn.port,
        'username': conn.username,
        'status': conn.status.name.lower()
    } for conn in connections]
    
    return jsonify(connections_data)

@app.route('/api/ssh/connections/<connection_id>', methods=['DELETE'])
def close_ssh_connection(connection_id):
    """Close an SSH connection"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    success = ztalk_app.close_ssh_connection(connection_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to close connection'}), 400

# SSH profile endpoints
@app.route('/api/ssh/profiles', methods=['POST'])
def save_ssh_profile():
    """Save an SSH connection profile"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    data = request.get_json()
    name = data.get('name')
    host = data.get('host')
    port = data.get('port', 22)
    username = data.get('username', '')
    key_path = data.get('keyPath')
    
    if not name or not host:
        return jsonify({'error': 'Name and host are required'}), 400
        
    profile_id = ztalk_app.save_ssh_profile(
        name=name,
        host=host,
        port=port,
        username=username,
        key_path=key_path
    )
    
    if profile_id:
        return jsonify({'profileId': profile_id, 'success': True})
    else:
        return jsonify({'error': 'Failed to save SSH profile'}), 400

@app.route('/api/ssh/profiles/<profile_id>', methods=['DELETE'])
def delete_ssh_profile(profile_id):
    """Delete an SSH profile"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    success = ztalk_app.delete_ssh_profile(profile_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to delete profile'}), 400

@app.route('/api/ssh/profiles/<profile_id>', methods=['GET'])
def get_ssh_profile(profile_id):
    """Get a specific SSH profile"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    profile = ztalk_app.get_ssh_profile(profile_id)
    
    if profile:
        return jsonify(profile)
    else:
        return jsonify({'error': 'Profile not found'}), 404

@app.route('/api/ssh/profiles', methods=['GET'])
def get_all_ssh_profiles():
    """Get all SSH profiles"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    profiles = ztalk_app.get_all_ssh_profiles()
    return jsonify(profiles)

@app.route('/api/ssh/profiles/<profile_id>/connect', methods=['POST'])
def connect_from_ssh_profile(profile_id):
    """Create a connection from an SSH profile"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    data = request.get_json()
    password = data.get('password')
    
    connection_id = ztalk_app.connect_from_ssh_profile(profile_id, password)
    
    if connection_id:
        return jsonify({'connectionId': connection_id, 'success': True})
    else:
        return jsonify({'error': 'Failed to connect from profile'}), 400

# Group management endpoints
@app.route('/api/groups', methods=['POST'])
def create_group():
    """Create a new message group"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    data = request.get_json()
    group_name = data.get('groupName')
    peer_ids = data.get('peerIds', [])
    
    if not group_name:
        return jsonify({'error': 'Group name is required'}), 400
        
    group_id = ztalk_app.create_group(group_name, peer_ids)
    
    return jsonify({'groupId': group_id, 'name': group_name, 'success': True})

@app.route('/api/groups/<group_id>/members/<peer_id>', methods=['POST'])
def add_to_group(group_id, peer_id):
    """Add a peer to a group"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    success = ztalk_app.add_to_group(group_id, peer_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to add peer to group'}), 400

@app.route('/api/groups/<group_id>/members/<peer_id>', methods=['DELETE'])
def remove_from_group(group_id, peer_id):
    """Remove a peer from a group"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    success = ztalk_app.remove_from_group(group_id, peer_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to remove peer from group'}), 400

@app.route('/api/groups/<group_id>', methods=['DELETE'])
def delete_group(group_id):
    """Delete a group"""
    if not ztalk_app:
        return jsonify({'error': 'Application not initialized'}), 500
        
    success = ztalk_app.delete_group(group_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to delete group'}), 400

# Main API entry point
@app.route('/api', methods=['GET'])
def api_info():
    """API info endpoint"""
    return jsonify({
        'name': 'ZTalk API',
        'version': '1.0.0',
        'status': 'running' if ztalk_app else 'initializing'
    })

# Socket.IO connection handlers
@socketio.on('connect')
def handle_connect():
    """Handle new Socket.IO connections"""
    logger.info(f"New client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle Socket.IO disconnections"""
    logger.info(f"Client disconnected: {request.sid}")

if __name__ == '__main__':
    # Initialize ZTalk application
    if not init_ztalk_app():
        logger.error("Failed to initialize ZTalk application")
        sys.exit(1)
    
    # Start the server
    try:
        logger.info("Starting API server on http://localhost:5000")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if ztalk_app:
            ztalk_app.stop() 