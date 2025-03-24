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

# Check if all dependencies are installed
if ! pip freeze | diff -u - requirements.txt >/dev/null 2>&1; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "Dependencies already installed"
fi


# Run the Python script
echo "Running ztalk..."
python ./ztalk/main.py
