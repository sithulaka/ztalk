#!/bin/bash

# Check if compatibility modules exist
if [ ! -f "netifaces_compat.py" ]; then
    echo "Creating netifaces compatibility module..."
    touch netifaces_compat.py
    echo "#!/usr/bin/env python3
import sys
import logging
logging.warning('netifaces_compat.py is empty. Please run the setup script first.')
sys.exit(1)" > netifaces_compat.py
    chmod +x netifaces_compat.py
fi

if [ ! -f "zeroconf_compat.py" ]; then
    echo "Creating zeroconf compatibility module..."
    touch zeroconf_compat.py
    echo "#!/usr/bin/env python3
import sys
import logging
logging.warning('zeroconf_compat.py is empty. Please run the setup script first.')
sys.exit(1)" > zeroconf_compat.py
    chmod +x zeroconf_compat.py
fi

# Make sure compatibility modules are executable
chmod +x netifaces_compat.py zeroconf_compat.py

# Check if packages are installed locally
if ! python3 -c "import zeroconf" &>/dev/null; then
    echo "Zeroconf not found. Installing packages locally..."
    ./pip_local_install.sh
fi

# Check if netifaces is available
if ! python3 -c "import netifaces" &>/dev/null; then
    echo "Netifaces not found. Will use fallback implementation."
    # Test the compatibility module
    python3 netifaces_compat.py
fi

# Run the application
echo "Running ZTalk..."
python3 ./main.py