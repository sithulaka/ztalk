#!/usr/bin/env python3
"""
ZTalk SSH Client Example

This example demonstrates how to use the SSH client to connect to a remote server.
"""

import os
import sys
import time
import logging
import argparse
from typing import Optional

# Add parent directory to path to import ZTalk packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.ssh_client import SSHClient
from ui.notification import Notification

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('ssh_example')

def main():
    """Main entry point for the SSH example"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ZTalk SSH Client Example")
    parser.add_argument('--host', type=str, help='SSH server hostname or IP', required=True)
    parser.add_argument('--port', type=int, default=22, help='SSH server port')
    parser.add_argument('--username', type=str, required=True, help='SSH username')
    parser.add_argument('--password', type=str, help='SSH password (not recommended, use key-based auth instead)')
    parser.add_argument('--key', type=str, help='Path to SSH private key')
    parser.add_argument('--name', type=str, help='Connection name')
    parser.add_argument('--save-profile', action='store_true', help='Save connection as a profile')
    
    args = parser.parse_args()
    
    # Create SSH client
    ssh_client = SSHClient()
    
    try:
        # If saving as a profile
        if args.save_profile:
            profile_id = ssh_client.save_profile(
                name=args.name or f"{args.username}@{args.host}",
                host=args.host,
                port=args.port,
                username=args.username,
                key_path=args.key
            )
            print(f"Saved SSH profile: {profile_id}")
            
            # Connect from profile
            connection_id = ssh_client.connect_from_profile(
                profile_id=profile_id,
                password=args.password
            )
        else:
            # Connect directly
            connection_id = ssh_client.connect(
                host=args.host,
                port=args.port,
                username=args.username,
                password=args.password,
                key_path=args.key,
                name=args.name
            )
        
        if not connection_id:
            print("Failed to create SSH connection")
            return 1
            
        print(f"Created SSH connection with ID: {connection_id}")
        print("Terminal window will open automatically...")
        
        # Keep the main thread alive until all terminal windows are closed
        while ssh_client.active_terminals:
            time.sleep(0.1)
            
        print("All SSH connections closed, exiting...")
        
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        # Clean up
        ssh_client.stop()
        
    return 0

if __name__ == "__main__":
    sys.exit(main()) 