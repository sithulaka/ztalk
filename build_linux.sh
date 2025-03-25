#!/bin/bash

echo "Building ZTalk for Linux..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python not found. Please install Python 3.6+ and try again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Make sure python3-venv is installed."
        echo "On Debian/Ubuntu: sudo apt-get install python3-venv"
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
pip install pyinstaller

# Get Python version for path
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

# Build with PyInstaller
echo "Building application..."
pyinstaller --noconfirm --onedir --windowed \
    --name ZTalk \
    --add-data ".venv/lib/python${PYTHON_VERSION}/site-packages/customtkinter:customtkinter/" \
    main.py

# Create .desktop file for easy launching
echo "Creating .desktop file..."
cat > dist/ZTalk/ZTalk.desktop << EOL
[Desktop Entry]
Name=ZTalk
Comment=Cross-platform P2P chat application
Exec=$(pwd)/dist/ZTalk/ZTalk
Icon=$(pwd)/docs/icon.png
Terminal=false
Type=Application
Categories=Network;Chat;
EOL

# Make desktop file executable
chmod +x dist/ZTalk/ZTalk.desktop

# Create tar.gz package
echo "Creating tar.gz package..."
tar -czf dist/ZTalk-linux.tar.gz -C dist ZTalk

echo "Build completed. The executable is located in dist/ZTalk/ZTalk"
echo "A compressed package is available at dist/ZTalk-linux.tar.gz"

# Deactivate virtual environment
deactivate

echo "Build process finished!" 