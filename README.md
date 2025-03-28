# ZTalk

ZTalk is a modern zero-configuration messaging and SSH management application for local networks.

## Features

- **Zero-Configuration Networking:** Automatically discovers peers on the local network without any setup
- **Real-time Messaging:** Chat with peers on your network with support for private, group, and broadcast messages
- **SSH Connection Management:** Manage multiple SSH connections with a user-friendly interface
- **Network Diagnostics Tools:** Scan your network, perform latency tests, and manage IP configurations
- **Dual Interfaces:** Modern React web UI and terminal-based UI options

## Installation

### Prerequisites

- Python 3.8 or higher
- Node.js (v14 or newer)
- npm or yarn

### Quick Installation

The easiest way to install and run ZTalk is using the provided `run.sh` script:

```bash
git clone https://github.com/yourusername/ztalk.git
cd ztalk
./run.sh
```

This script will:
1. Set up a Python virtual environment
2. Install Python dependencies
3. Install npm dependencies if needed
4. Start the application

### Manual Installation

If you prefer to install manually:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ztalk.git
   cd ztalk
   ```

2. Set up Python environment and dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   pip install flask flask-cors flask-socketio
   ```

3. Install Node.js dependencies:
   ```bash
   npm install
   ```

## Running the Application

ZTalk can be run in multiple modes:

### Web Interface (Default)

Run both the API server and React frontend:

```bash
./run.sh
# or
./run.sh web
# or
npm run dev
```

This will start:
- Flask API server at `http://localhost:5000`
- React frontend at `http://localhost:3000`

### Terminal Interface

```bash
./run.sh terminal
# or
python main.py
```

### API Server Only

```bash
./run.sh api
# or
python app.py
```

### Examples

Run any of the included examples:

```bash
./run.sh demo
# or
python ztalk.py demo
```

## Entry Points

ZTalk has multiple entry points depending on your needs:

1. **app.py** - The Flask API server connecting the React frontend with the ZTalk backend
2. **main.py** - The terminal UI version of ZTalk
3. **ztalk.py** - A launcher script for running different examples/components

## Building for Production

```bash
npm run electron:build
```

This will create platform-specific installers in the `dist` directory.

## Publishing to GitHub

To publish ZTalk to GitHub:

1. Create a new GitHub repository:
   ```bash
   git init  # If not already a git repository
   git add .
   git commit -m "Initial commit of ZTalk"
   ```

2. Connect to your GitHub repository:
   ```bash
   git remote add origin https://github.com/yourusername/ztalk.git
   ```

3. Push your code:
   ```bash
   git push -u origin main  # or master depending on your branch name
   ```

### Creating a Release

1. Tag your release version:
   ```bash
   git tag -a v1.0.0 -m "ZTalk version 1.0.0"
   git push origin v1.0.0
   ```

2. On GitHub, go to Releases and create a new release from your tag

3. Include release notes and any pre-built binaries if you have them

## Architecture

ZTalk is built with modern web technologies:

- **Frontend:** React, TypeScript, TailwindCSS
- **Backend:** Flask API, Python core, Electron integration
- **Networking:** socket.io, zeroconf/bonjour
- **SSH:** paramiko (Python), ssh2 (Node.js)

## Troubleshooting

### API Server Issues

If you encounter issues with the Flask API server related to Werkzeug:

```
RuntimeError: The Werkzeug web server is not designed to run in production.
```

This is fixed in the latest version by adding `allow_unsafe_werkzeug=True`. If you're still seeing this error, run:

```bash
sed -i 's/socketio.run(app, host='\''0.0.0.0'\'', port=5000, debug=True, use_reloader=False)/socketio.run(app, host='\''0.0.0.0'\'', port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)/g' app.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 