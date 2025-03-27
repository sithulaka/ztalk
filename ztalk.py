#!/usr/bin/env python3
"""
ZTalk Application Launcher

This script serves as the main entry point for the ZTalk application.
It provides a simple interface to launch different components or examples.
"""

import sys
import os
import argparse
import logging
import importlib
from typing import List, Dict, Optional

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('ztalk')

# Available examples/components to launch
AVAILABLE_COMPONENTS = {
    "demo": "examples.ztalk_demo",
    "chat": "examples.chat_example",
    "ssh": "examples.ssh_example",
    "multi-ssh": "examples.multi_ssh_example",
}

def show_banner():
    """Display a welcome banner"""
    print(r"""
  _______ _____ _    _ _      _  __
 |__   __|_   _/ \  | | |    | |/ /
    | |    | || |  | | |    | ' / 
    | |    | || |__| | |___ | . \ 
    |_|    |_|\____/|_____||_|\_\
    
  Zero-Configuration Networking & SSH Tool
  
""")

def run_component(component_name: str, args: List[str]):
    """
    Run a specific component by name with the provided arguments.
    
    Args:
        component_name: The name of the component to run
        args: Command line arguments to pass to the component
    """
    if component_name not in AVAILABLE_COMPONENTS:
        logger.error(f"Unknown component: {component_name}")
        show_available_components()
        return 1
        
    # Import the module dynamically
    module_name = AVAILABLE_COMPONENTS[component_name]
    try:
        module = importlib.import_module(module_name)
        
        # Replace sys.argv with our filtered arguments
        orig_argv = sys.argv
        sys.argv = [module_name] + args
        
        # Run the module's main function
        result = module.main()
        
        # Restore original argv
        sys.argv = orig_argv
        
        return result
    except ImportError as e:
        logger.error(f"Error importing {module_name}: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error running {module_name}: {e}")
        return 1

def show_available_components():
    """Display available components that can be launched"""
    print("\nAvailable components:")
    for name, module in AVAILABLE_COMPONENTS.items():
        print(f"  {name:<10} - {module}")
    print("\nExample usage:")
    print("  python ztalk.py demo --username John")
    print("  python ztalk.py chat --debug")
    print("  python ztalk.py ssh --host example.com --username admin")
    print("")

def main():
    """Main entry point for the ZTalk launcher"""
    # Parse just the first argument to determine which component to run
    parser = argparse.ArgumentParser(description="ZTalk Application Launcher")
    parser.add_argument('component', nargs='?', help='Component to launch')
    parser.add_argument('--list', action='store_true', help='List available components')
    
    # Parse only the known arguments
    args, remaining = parser.parse_known_args()
    
    # Show banner
    show_banner()
    
    # If --list is specified or no component is provided, show available components
    if args.list or not args.component:
        show_available_components()
        return 0
        
    # Run the specified component with the remaining arguments
    return run_component(args.component, remaining)

if __name__ == "__main__":
    sys.exit(main()) 