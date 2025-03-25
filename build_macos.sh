#!/bin/bash

echo "Building ZTalk for macOS..."

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
        echo "Failed to create virtual environment. Make sure venv is available."
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
    --icon=docs/icon.icns \
    --add-data ".venv/lib/python${PYTHON_VERSION}/site-packages/customtkinter:customtkinter/" \
    main.py

# Create a DMG file
echo "Creating DMG file..."
mkdir -p dist/dmg
cp -r dist/ZTalk dist/dmg/
hdiutil create -volname "ZTalk" -srcfolder dist/dmg -ov -format UDZO dist/ZTalk.dmg

echo "Build completed. The app is located in dist/ZTalk.app"
echo "A DMG installer is available at dist/ZTalk.dmg"

# Deactivate virtual environment
deactivate

echo "Build process finished!"