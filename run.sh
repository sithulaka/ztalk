#!/bin/bash

for iface in $(ip -o link show | awk -F': ' '{print $2}'); do
    for ip in $(ip addr show dev $iface | grep 'inet ' | awk '{print $2}'); do
        sudo ip addr del $ip dev $iface
    done
done
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

# Check if requirements are installed
if ! pip freeze | grep -q "zeroconf"; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "Dependencies already installed"
fi


# Run the Python script
echo "Running ztalk..."
python main.py
