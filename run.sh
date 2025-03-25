#!/bin/bash

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE=Linux;;
    Darwin*)    OS_TYPE=MacOS;;
    CYGWIN*)    OS_TYPE=Windows;;
    MINGW*)     OS_TYPE=Windows;;
    MSYS*)      OS_TYPE=Windows;;
    *)          OS_TYPE="UNKNOWN:${OS}"
esac

echo "Detected OS: $OS_TYPE"

# Function for Linux setup
setup_linux() {
    # Check for python3-venv
    if ! dpkg -l | grep -q python3-venv; then
        echo "Installing python3-venv..."
        sudo apt-get update
        sudo apt-get install -y python3-venv
    fi

    # Set up sudo permissions for network monitoring if needed
    if [ ! -f "/etc/sudoers.d/ztalk" ]; then
        echo "Setting up network monitoring permissions..."
        echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/ip" | sudo tee /etc/sudoers.d/ztalk
    fi
}

# Function for macOS setup
setup_macos() {
    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi

    # Check for Python
    if ! command -v python3 &> /dev/null; then
        echo "Installing Python3 with Homebrew..."
        brew install python
    fi
}

# Function for Windows setup
setup_windows() {
    echo "Windows detected. No additional setup required."
    # Windows-specific setup could go here
}

# OS-specific setup
case "${OS_TYPE}" in
    Linux)  setup_linux;;
    MacOS)  setup_macos;;
    Windows) setup_windows;;
    *)      echo "Unsupported OS: $OS_TYPE. Proceeding with basic setup.";;
esac

# Setup virtual environment (cross-platform)
if [ -z "$VIRTUAL_ENV" ]; then
    # Check if virtual environment exists
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv .venv || {
            echo "Failed to create virtual environment. Please ensure python3-venv is installed."
            exit 1
        }
    fi
    
    echo "Activating virtual environment..."
    # Source activation script based on OS
    case "${OS_TYPE}" in
        Windows)
            source .venv/Scripts/activate || {
                echo "Failed to activate virtual environment."
                exit 1
            }
            ;;
        *)
            source .venv/bin/activate || {
                echo "Failed to activate virtual environment."
                exit 1
            }
            ;;
    esac
else
    echo "Virtual environment already active"
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt || {
    echo "Failed to install dependencies."
    exit 1
}

# Run the Python script
echo "Running ZTalk..."
python main.py