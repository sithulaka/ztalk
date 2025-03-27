#!/bin/bash
# This script creates a symbolic link to the system netifaces module in the virtual environment

# Find the system netifaces module path
SYSTEM_NETIFACES_PATH=$(python3 -c "import sys; print(next((p for p in sys.path if '/usr/lib/python' in p), ''))")
if [ -z "$SYSTEM_NETIFACES_PATH" ]; then
    echo "Could not find system Python path."
    exit 1
fi

# Check if netifaces exists in system path
if [ ! -e "$SYSTEM_NETIFACES_PATH/netifaces.py" ] && [ ! -d "$SYSTEM_NETIFACES_PATH/netifaces" ]; then
    echo "Could not find netifaces module in system Python path."
    
    # Try finding in dist-packages
    DIST_PACKAGES=$(find /usr/lib/python3* -name "dist-packages" -type d 2>/dev/null | head -n 1)
    if [ -n "$DIST_PACKAGES" ]; then
        if [ -e "$DIST_PACKAGES/netifaces.py" ] || [ -d "$DIST_PACKAGES/netifaces" ]; then
            SYSTEM_NETIFACES_PATH="$DIST_PACKAGES"
            echo "Found netifaces in $SYSTEM_NETIFACES_PATH"
        fi
    fi
    
    if [ ! -e "$SYSTEM_NETIFACES_PATH/netifaces.py" ] && [ ! -d "$SYSTEM_NETIFACES_PATH/netifaces" ]; then
        echo "Please install netifaces system-wide first with:"
        echo "sudo apt-get install python3-netifaces"
        exit 1
    fi
fi

# Ensure virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "Virtual environment not found. Please activate it first."
        exit 1
    fi
fi

# Get the site-packages directory of the virtual environment
VENV_SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")

# Create symbolic link
if [ -e "$SYSTEM_NETIFACES_PATH/netifaces.py" ]; then
    echo "Creating symbolic link for netifaces.py"
    ln -sf "$SYSTEM_NETIFACES_PATH/netifaces.py" "$VENV_SITE_PACKAGES/netifaces.py"
    echo "Linked $SYSTEM_NETIFACES_PATH/netifaces.py to $VENV_SITE_PACKAGES/netifaces.py"
elif [ -d "$SYSTEM_NETIFACES_PATH/netifaces" ]; then
    echo "Creating symbolic link for netifaces directory"
    ln -sf "$SYSTEM_NETIFACES_PATH/netifaces" "$VENV_SITE_PACKAGES/netifaces"
    echo "Linked $SYSTEM_NETIFACES_PATH/netifaces to $VENV_SITE_PACKAGES/netifaces"
else
    echo "Could not find netifaces module or package."
    exit 1
fi

# Create an empty __init__.py if needed
if [ ! -e "$VENV_SITE_PACKAGES/netifaces/__init__.py" ] && [ -d "$VENV_SITE_PACKAGES/netifaces" ]; then
    touch "$VENV_SITE_PACKAGES/netifaces/__init__.py"
    echo "Created empty __init__.py in $VENV_SITE_PACKAGES/netifaces/"
fi

echo "Netifaces fix completed. Try running your application again." 