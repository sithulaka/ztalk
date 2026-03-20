# ZTalk

Zero-configuration peer-to-peer messaging, SSH management, and network tools for local networks. Peers are discovered automatically via mDNS — no manual IP setup required. Chat in real time, manage SSH sessions, run network diagnostics, and optionally spin up a DHCP server on isolated networks.

## How It Works

ZTalk runs a **Python backend** (Flask) that handles peer discovery, messaging, SSH connections, and networking. A **React frontend** talks to the backend over REST and WebSocket (Socket.IO). The whole thing can also be packaged as an **Electron desktop app**.

```
┌─────────────────────────────────────────────────────────┐
│  React Frontend (localhost:3000)                        │
│  Dashboard │ Chat │ SSH │ Network Tools │ Settings      │
└──────────────────────┬──────────────────────────────────┘
                       │ REST + WebSocket (Socket.IO)
┌──────────────────────▼──────────────────────────────────┐
│  Flask API Server (localhost:5000)                       │
│  Auth (Bearer token) │ CSRF │ Rate limiting             │
└──┬─────────┬──────────┬──────────┬──────────┬───────────┘
   │         │          │          │          │
   ▼         ▼          ▼          ▼          ▼
 Peer     Message    SSH       Network     DHCP
 Discovery Handler   Manager   Manager     Server
 (mDNS)   (Fernet)  (Paramiko)            (optional)
```

### Peer Discovery

On startup, ZTalk registers itself on the local network using Zeroconf/mDNS (service type `_ztalk._tcp.local.`). Other ZTalk instances on the same LAN are discovered automatically. A background thread monitors peer health and marks stale peers as inactive.

### Messaging

Messages travel peer-to-peer over UDP sockets. Three modes: **private** (one-to-one), **group** (named channel), and **broadcast** (all peers). Optional Fernet encryption with per-message random salt (PBKDF2 key derivation). Messages include delivery acknowledgments with retry (up to 3 attempts). Message deduplication prevents duplicates from network retries. History is thread-safe and persisted to the browser's localStorage (capped at 1000 messages).

### SSH Manager

Create and manage multiple simultaneous SSH sessions via Paramiko. Connection profiles can be saved (passwords are never written to disk). Host keys are stored in `~/.ztalk/known_hosts`. All SSH operations are audit-logged (without credentials).

### Network Tools

Detects active network interfaces, scans for devices, and provides diagnostics. Interface names are validated to prevent injection. On the frontend, you can view interface details, monitor bandwidth stats, and apply IP configuration.

### DHCP Server

Optional built-in DHCP server for isolated networks (default `192.168.100.0/24`). Configurable network range and DNS servers. Periodic lease cleanup runs every 5 minutes.

## Project Structure

```
ztalk/
├── app.py                  # Flask API server (REST + WebSocket)
├── main.py                 # Terminal UI entry point (CustomTkinter)
├── ztalk.py                # Demo/component launcher
├── run.sh                  # Setup & launch script (venv, deps, checks)
├── core/
│   ├── application.py      # Central orchestrator — starts all subsystems
│   ├── peer_discovery.py   # Zeroconf/mDNS peer discovery (thread-safe)
│   ├── messaging.py        # Message routing, encryption, ack, dedup
│   ├── network_manager.py  # Interface detection, scanning, diagnostics
│   ├── ssh_manager.py      # SSH connections + host key management
│   └── dhcp_server.py      # Built-in DHCP server with lease cleanup
├── src/                    # React frontend (TypeScript + Tailwind)
│   ├── pages/
│   │   ├── Dashboard.tsx   # Overview: active peers, recent messages, groups
│   │   ├── Chat.tsx        # Messaging UI with markdown (sanitized)
│   │   ├── SSH.tsx         # SSH connection management
│   │   ├── NetworkTools.tsx# Interface viewer, diagnostics
│   │   └── Settings.tsx    # Username, theme, notification preferences
│   ├── components/         # Layout, ErrorBoundary
│   ├── contexts/           # NetworkContext, ThemeContext (3 themes)
│   └── services/           # Axios API client with error interceptor
├── public/
│   ├── electron.js         # Electron main process (CSP, DevTools shortcut)
│   └── preload.js          # Secure bridge: API client + Socket.IO
├── ui/                     # Terminal GUI (CustomTkinter)
│   ├── chat_window.py      # Chat UI with themed colors
│   ├── ssh_client.py       # SSH terminal UI
│   ├── terminal_widget.py  # Terminal emulator widget
│   └── notification.py     # Desktop notifications
├── utils/                  # SSH, platform, and Windows utilities
├── examples/               # Demo scripts (chat, SSH, multi-SSH)
├── tests/                  # pytest test suite (76 tests)
├── .env.example            # Environment variable template
├── requirements.txt        # Python runtime dependencies
└── requirements-dev.txt    # Dev dependencies (pytest, black, flake8, mypy)
```

## Prerequisites

- Python 3.8+
- Node.js 14+
- `python3-tk` (system package, only needed for terminal UI)

## Quick Start

```bash
git clone <repo-url>
cd ztalk
./run.sh
```

`run.sh` handles everything: creates a Python venv, installs dependencies, checks Node.js version, and launches the app. On exit, background processes are cleaned up automatically via trap.

### Manual Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
```

Then pick an entry point:

```bash
python app.py          # API server on localhost:5000
npm run dev            # API + React dev server (localhost:3000)
python main.py         # Terminal UI (requires python3-tk)
```

## Run Modes

| Command | What it does |
|---------|-------------|
| `./run.sh` or `./run.sh web` | Flask API (port 5000) + React dev server (port 3000) |
| `./run.sh terminal` | Terminal GUI via `python main.py` |
| `./run.sh api` | API server only |
| `./run.sh demo` | Interactive demo via `python ztalk.py demo` |

### npm Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | API + React dev server together |
| `npm run dev:electron` | API + Electron dev |
| `npm run build` | Production React build |
| `npm run electron:build` | Build Electron desktop app |

## API

All endpoints (except `GET /api`) require a Bearer token in the `Authorization` header. The token is printed to console on startup. State-changing requests (POST/PUT/DELETE) also require an `X-CSRF-Token` header obtained from `GET /api/csrf-token`. Rate limit: 60 requests/minute default, 10/second on message endpoints.

### Authentication

```bash
# Get the token from server startup output:
# API_TOKEN=abc123...

# Use it in requests:
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/peers/active

# For POST/PUT/DELETE, also get a CSRF token first:
CSRF=$(curl -s -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/csrf-token | jq -r .csrfToken)
curl -X POST -H "Authorization: Bearer $TOKEN" -H "X-CSRF-Token: $CSRF" \
     -H "Content-Type: application/json" \
     -d '{"content":"hello"}' http://localhost:5000/api/messages/broadcast
```

### Endpoints

| Area | Endpoints |
|------|-----------|
| Health | `GET /api` (no auth) |
| Auth | `GET /api/csrf-token` |
| User | `GET/POST /api/user/username` |
| Peers | `GET /api/peers/active`, `GET /api/peers/all` |
| Messages | `POST /api/messages/private/<id>`, `POST /api/messages/broadcast`, `POST /api/messages/group/<id>`, `GET /api/messages/history?limit=50&offset=0`, `DELETE /api/messages/clear` |
| Network | `GET /api/network/interfaces`, `GET /api/network/interfaces/<name>`, `POST /api/network/interfaces/<name>/config`, `GET /api/network/scan` |
| DHCP | `GET /api/dhcp/status`, `POST /api/dhcp/config`, `GET /api/dhcp/leases` |
| SSH | `POST /api/ssh/connect`, `GET /api/ssh/connections`, `DELETE /api/ssh/connections/<id>`, CRUD on `/api/ssh/profiles` |
| Groups | `POST /api/groups`, `POST/DELETE /api/groups/<id>/members/<peer_id>`, `DELETE /api/groups/<id>` |

### WebSocket Events (Socket.IO)

| Event | Payload | Description |
|-------|---------|-------------|
| `peer_event` | `{event, peerId, name, ipAddress}` | Peer discovered/lost |
| `message_event` | `{messageId, type, content, senderId, senderName}` | New message |
| `network_change` | `{event, interfaceName, newIp, oldIp}` | Interface added/changed/removed |
| `dhcp_event` | `{event, enabled, network}` | DHCP config changed |
| `ssh_event` | `{event, connectionId, host, port}` | SSH connected/disconnected |

## Configuration

ZTalk stores its configuration in `~/.ztalk/`:

| File | Purpose |
|------|---------|
| `config.json` | App settings (encrypted at rest with Fernet) |
| `known_hosts` | SSH host key fingerprints |
| `logs/ztalk.log` | Rotating log file (5 MB, 3 backups) |

### Environment Variables

Copy `.env.example` to `.env` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `ZTALK_API_PORT` | `5000` | Flask API port |
| `ZTALK_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `REACT_APP_API_URL` | `http://localhost:5000/api` | API URL for frontend |

## Frontend

The React app has three themes: **light**, **dark**, and **dark blue** (auto-detects OS preference). Respects `prefers-reduced-motion` for accessibility. All interactive elements have ARIA labels and keyboard navigation.

### Pages

- **Dashboard** — Active peers count, recent messages, quick actions to navigate
- **Chat** — Select a peer or group, send messages with sanitized Markdown rendering
- **SSH** — Connect to hosts, manage saved profiles, terminal interface
- **Network Tools** — View interfaces, bandwidth stats, apply IP configuration
- **Settings** — Change username, select theme, toggle notifications

## Security

- Bearer token auth on all API endpoints (token generated on startup)
- CSRF tokens required for state-changing requests
- Rate limiting (60/min default, 10/sec on messaging)
- Message content validated (max 10,000 chars, null bytes stripped)
- Socket.IO CORS restricted to `localhost:3000`
- Electron Content Security Policy headers
- SSH host keys verified against `~/.ztalk/known_hosts`
- SSH passwords cleared from memory after connection, never saved to disk
- Config file encrypted at rest (Fernet + PBKDF2)
- Subprocess calls use list form (no shell injection)
- Markdown rendering restricted to safe HTML elements
- Interface names validated against regex before use in commands

## Testing

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -v
```

76 tests covering API auth, CSRF, input validation, message handling, peer discovery, SSH security, and infrastructure.

## Building the Desktop App

```bash
npm run electron:build
```

Creates platform-specific installers in `dist/`. DevTools can be toggled with `Ctrl+Shift+I` (or `Cmd+Option+I` on Mac).

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | React 18, TypeScript, Tailwind CSS, DaisyUI |
| Backend | Flask, Flask-SocketIO, Flask-Limiter |
| Desktop | Electron 25, electron-builder |
| Networking | Zeroconf/mDNS, Socket.IO, Axios |
| SSH | Paramiko |
| Encryption | cryptography (Fernet, PBKDF2) |
| Testing | pytest, pytest-cov |

## License

MIT
