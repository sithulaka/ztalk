#!/bin/bash
# Check if already in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv .venv
    fi
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "Virtual environment already active"
fi

# Check and install only missing dependencies
echo "Checking dependencies..."
pip install -r requirement.txt

echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/ip" | sudo tee /etc/sudoers.d/ztalk

# Run the Python script
echo "Running ztalk..."
python ./main.py