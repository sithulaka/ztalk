#!/bin/bash
# Script to install Python packages locally for the current user

# Install zeroconf and dependencies
pip install --user --break-system-packages zeroconf 

# Install other necessary packages
pip install --user --break-system-packages cryptography pygments prompt_toolkit paramiko

# Install UI dependencies
pip install --user --break-system-packages customtkinter pillow CTkMessagebox

echo "Packages installed locally for the current user."
echo "You can now run the application with: python main.py" 