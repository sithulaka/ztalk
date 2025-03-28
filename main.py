#!/usr/bin/env python3
"""
ZTalk - Zero Configuration Terminal Chat Application

A terminal-based chat application that automatically discovers peers on the local network
and enables real-time group and private conversations with SSH capabilities.
"""

import argparse
import logging
import sys
import os
import signal
import time
from typing import Optional

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core import ZTalkApp
from ui import ChatWindow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)

# Create log directory if it doesn't exist
log_dir = os.path.expanduser('~/.ztalk')
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

# Add file handler for logs
logging.getLogger().addHandler(
    logging.FileHandler(os.path.join(log_dir, 'ztalk.log'))
)

# Create logger
logger = logging.getLogger('ztalk')

# Global app instance
app: Optional[ZTalkApp] = None

def signal_handler(sig, frame):
    """Handle interrupt signals"""
    print("\nShutting down ZTalk...")
    if app:
        app.stop()
    sys.exit(0)

def main():
    """Main entry point for ZTalk application"""
    global app
    
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="ZTalk - Zero Configuration Terminal Chat Application"
    )
    parser.add_argument(
        '--debug', 
        action='store_true', 
        help='Enable debug logging'
    )
    parser.add_argument(
        '--username', 
        type=str, 
        help='Set your display name'
    )
    parser.add_argument(
        '--scan', 
        action='store_true', 
        help='Scan network for ZTalk peers and exit'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logging.getLogger('core').setLevel(logging.DEBUG)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create application instance
        app = ZTalkApp()
        
        # Set username if provided
        if args.username:
            app.set_username(args.username)
        
        # Start the application
        if not app.start():
            logger.error("Failed to start ZTalk application")
            return 1
            
        # If scan mode, just report discovered peers and exit
        if args.scan:
            print("Scanning network for ZTalk peers...")
            # Give some time for discovery
            time.sleep(5)
            
            peers = app.get_active_peers()
            if peers:
                print(f"Found {len(peers)} ZTalk peers:")
                for peer in peers:
                    print(f"  - {peer.name} ({peer.ip_address})")
            else:
                print("No ZTalk peers found on the network.")
                
            app.stop()
            return 0
            
        # Launch the UI
        logger.info("Launching ZTalk UI...")
        chat_window = ChatWindow(
            username=app.username, 
            send_private_msg=app.send_message,
            send_broadcast=app.broadcast_message,
            get_peers=app.get_active_peers,
            network_manager=app.network_manager,
            enable_dhcp=app.enable_dhcp,
            get_dhcp_status=app.get_dhcp_status
        )
        chat_window.mainloop()
        
        # When UI is closed, shut down the application
        app.stop()
        return 0
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        if app:
            app.stop()
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())