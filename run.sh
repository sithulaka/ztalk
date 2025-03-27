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

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --break-system-packages || {
    echo "Failed to install dependencies."
    exit 1
}

# Run the Python script
echo "Running ztalk..."
python ./main.py