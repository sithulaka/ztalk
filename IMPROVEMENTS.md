# ZTalk — Improvements Roadmap

> Generated: 2026-03-20

## Summary

| Severity | Count |
|----------|-------|
| Critical | 10 |
| High | 18 |
| Medium | 22 |
| Low | 12 |
| **Total** | **62** |

---

## Critical

### 1. No API Authentication or Authorization

**Files:** `app.py` (all endpoints)

All 37+ REST endpoints and WebSocket events are completely unprotected. Any client on the network can control peers, read messages, manage SSH connections, and configure DHCP.

**Fix:** Add token-based auth (JWT or session tokens). At minimum, require an API key header for all requests.

---

### 2. Socket.IO CORS Allows All Origins

**File:** `app.py:36`

```python
socketio = SocketIO(app, cors_allowed_origins="*")
```

Flask CORS is restricted to `localhost:3000`, but Socket.IO accepts connections from any origin. Any website can open a WebSocket to your server and access real-time peer/message data.

**Fix:** `cors_allowed_origins="http://localhost:3000"`

---

### 3. Hardcoded Encryption Salt

**File:** `core/messaging.py:361`

```python
salt = b'ZTalk_salt_value'
```

The PBKDF2 salt is the same for every installation. All keys derived from the same password are identical across all ZTalk instances, defeating the purpose of salting.

**Fix:** Generate a random 16-byte salt per encryption context, transmit it alongside the ciphertext.

---

### 4. SSH AutoAddPolicy Accepts All Host Keys

**Files:** `core/ssh_manager.py:92`, `utils/ssh_utils.py:159,235,321,404,585`

```python
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
```

Every SSH connection blindly accepts unknown host keys, making all connections vulnerable to man-in-the-middle attacks.

**Fix:** Use `paramiko.RejectPolicy()` by default. Implement a `known_hosts` file at `~/.ztalk/known_hosts` and prompt the user to accept new keys.

---

### 5. SSH Credentials Stored in Plain Text

**File:** `core/ssh_manager.py:47,103`

Passwords and key paths are stored directly in `SSHConnection` objects in memory and written to config as plain JSON.

**Fix:** Use the `keyring` library for credential storage. Clear passwords from memory after connection is established. Never write passwords to config files.

---

### 6. No Content Security Policy in Electron

**File:** `public/electron.js`

The BrowserWindow has no CSP header set. A content injection vulnerability could load arbitrary scripts.

**Fix:** Add CSP via `session.defaultSession.webRequest.onHeadersReceived`:
```javascript
"default-src 'self'; script-src 'self'; connect-src 'self' http://localhost:5000 ws://localhost:5000"
```

---

### 7. No Testing Infrastructure

**Entire project**

Zero test files, no pytest config, no Jest setup, no CI/CD workflows. Every change is deployed untested.

**Fix:** Add `pytest` + `pytest-cov` for Python, `jest` + `@testing-library/react` for frontend. Create `.github/workflows/test.yml`. Start with API endpoint tests and core module unit tests.

---

### 8. Unsanitized Markdown Rendering (XSS Risk)

**File:** `src/pages/Chat.tsx:300`

```tsx
<ReactMarkdown>{msg.content}</ReactMarkdown>
```

Peer message content is rendered as markdown without sanitization. A malicious peer could inject HTML that ReactMarkdown passes through.

**Fix:** Configure ReactMarkdown with `allowedElements` whitelist, or pipe content through `dompurify` before rendering.

---

### 9. No Rate Limiting on Any Endpoint

**File:** `app.py` (all endpoints)

No limits on message sending, API calls, or WebSocket events. A single client can flood the server.

**Fix:** Add `flask-limiter`:
```python
limiter = Limiter(app, default_limits=["60/minute"])
@limiter.limit("10/second")
def send_message(): ...
```

---

### 10. Subprocess Shell Injection Risk

**File:** `core/network_manager.py:218`

Windows network commands use `shell=True` with user-controllable `interface` parameter.

**Fix:** Use list form: `subprocess.run(["netsh", "interface", ...], shell=False)` and validate interface names against `psutil.net_if_addrs()`.

---

## High

### 11. No Input Validation on Message Content

**File:** `app.py:212-237`

Messages are accepted with only a null check. No length limit, no content type validation.

**Fix:** Enforce `max_length=10000`, strip control characters, validate content is a string.

---

### 12. Stale Closures in SSH Component

**File:** `src/pages/SSH.tsx:147,171`

`handleConnect()` and `handleDisconnect()` reference `connections` inside `setTimeout` callbacks but `connections` isn't in the dependency array. The callback sees stale state.

**Fix:** Use functional state updates: `setConnections(prev => ...)` or add `connections` to the dependency array.

---

### 13. No Axios Error Interceptor

**File:** `src/services/api.ts`

No response interceptor for handling 401, 500, or network errors globally. Every component must handle errors independently.

**Fix:** Add interceptors:
```typescript
api.interceptors.response.use(
  response => response,
  error => { /* handle 401 redirect, show toast, etc. */ }
);
```

---

### 14. Race Condition in Peer Timeout Check

**File:** `core/peer_discovery.py:334-339`

`list(self.peers.items())` iterates the peer dict without a lock. Concurrent modifications from the discovery thread can cause `RuntimeError`.

**Fix:** Add `threading.Lock` around all `self.peers` access.

---

### 15. No Graceful Shutdown with Timeouts

**File:** `app.py:701-708`

`app.stop()` has no timeout. If any component hangs (stuck socket, blocking thread), the process never exits.

**Fix:** Add `timeout` parameter to thread joins. Use `signal.alarm()` or `threading.Timer` as a hard kill fallback.

---

### 16. Timer Leak in Message Retry

**File:** `core/messaging.py:515-547`

Retry timers are added to `_active_timers` but never removed when a message is acknowledged. The list grows indefinitely for long-running sessions.

**Fix:** Remove the timer from `_active_timers` in `_process_incoming_message` when an ACK is received. Also set a max retry count.

---

### 17. Bare Exception Catches Throughout Backend

**Files:** `core/network_manager.py:610,721,775`, `core/application.py` (multiple)

`except Exception:` with no logging or specific handling. Bugs silently disappear.

**Fix:** Catch specific exceptions. At minimum, log the traceback: `logger.exception("...")`.

---

### 18. run.sh Installs Wrong Package on Kali

**File:** `run.sh:54-55`

```bash
sudo apt-get install -y pypy3-venv
```

Installs `pypy3-venv` (PyPy) instead of `python3-venv` (CPython). The venv will fail to create.

**Fix:** `sudo apt-get install -y python3-venv`

---

### 19. run.sh Embeds 500+ Lines of Python

**File:** `run.sh:104-578`

`netifaces_compat.py` and `zeroconf_compat.py` are regenerated from embedded heredocs on every run. Hard to maintain, easy to introduce syntax errors.

**Fix:** Ship the compat modules as actual Python files in the repo. Only copy them if the real packages aren't available.

---

### 20. Electron Builder Missing Preload Script

**File:** `package.json:80-106`

The `files` array only includes `build/` and `node_modules/`. The `public/` directory (containing `electron.js` and `preload.js`) is not packaged.

**Fix:** Add `"public/**/*"` to the `files` array.

---

### 21. No Confirmation Dialogs for Destructive Actions

**Files:** `src/pages/SSH.tsx:178-195`, `src/pages/NetworkTools.tsx:241-270`

Deleting SSH connections and applying IP config changes happen on a single click with no confirmation.

**Fix:** Add a confirmation modal before SSH delete and IP config apply.

---

### 22. Settings Page is Empty

**File:** `src/pages/Settings.tsx:4-12`

The Settings page renders nothing useful. Users see a blank page.

**Fix:** Implement username editing, theme selection, notification preferences, and connection timeout settings. Or show "Coming soon" with a link to config file.

---

### 23. No Reconnection Logic for WebSocket

**File:** `public/preload.js:198-270`

Socket.IO connects once. If the connection drops, there's no automatic reconnect, no backoff, no user notification.

**Fix:** Enable Socket.IO's built-in reconnection with config: `io(url, { reconnection: true, reconnectionDelay: 1000, reconnectionAttempts: 10 })`.

---

### 24. Message History Not Persisted

**File:** `src/contexts/NetworkContext.tsx`

All messages are in React state only. Refreshing the page loses everything.

**Fix:** Persist to `localStorage` or `IndexedDB`. Load on mount, append on new message, cap at reasonable size (e.g., 1000 messages).

---

### 25. No Logging Infrastructure

**Entire project**

Logs go to console only. No rotation, no persistent files, no structured logging.

**Fix:** Use Python's `logging.handlers.RotatingFileHandler` writing to `~/.ztalk/logs/`. Add log levels configurable via env var.

---

### 26. Missing .env Support

**Files:** `public/preload.js:6`, `app.py:703`, `run.sh`

API URLs, ports, and hostnames are hardcoded across multiple files.

**Fix:** Create `.env.example` with all configurable values. Use `python-dotenv` for Python and `REACT_APP_*` env vars for the frontend.

---

### 27. Config File Not Encrypted

**File:** `core/application.py:557-595`

`~/.ztalk/config.json` stores groups, SSH hostnames, and usernames in plain JSON readable by any local user.

**Fix:** Encrypt config at rest using a machine-specific key (e.g., derived from hostname + user).

---

### 28. File Attachment Feature Not Implemented

**File:** `src/pages/Chat.tsx:54-62`

The file attachment button exists but the comment says "In a real implementation, we would upload the file." Files are just added as text.

**Fix:** Either implement file upload via a new `/api/messages/file` endpoint, or remove the button to avoid confusing users.

---

## Medium

### 29. No Message Deduplication

**File:** `core/messaging.py`

No check for duplicate message IDs. Network retries can deliver the same message twice.

**Fix:** Track recent message IDs in a bounded set (e.g., last 1000). Ignore duplicates.

---

### 30. Message History Dicts Not Thread-Safe

**File:** `core/messaging.py:572-594`

`private_histories` and `group_histories` are accessed from multiple threads without locks.

**Fix:** Add `threading.Lock` or use a thread-safe structure.

---

### 31. Encryption Failure Silently Drops Messages

**File:** `core/messaging.py:451-459`

If decryption fails, the message is logged as a warning and discarded. The sender never knows.

**Fix:** Send an error response to the sender. Consider negotiating encryption capability during peer discovery.

---

### 32. DHCP Lease Cleanup Only on Read

**File:** `core/dhcp_server.py`

Expired leases are only cleaned up when `get_leases()` is called. The `expired_leases` dict grows indefinitely otherwise.

**Fix:** Add a periodic cleanup timer (e.g., every 5 minutes) in a background thread.

---

### 33. No Message History Pagination

**File:** `app.py:276`

The `limit` query parameter accepts any integer. A client requesting `limit=10000000` gets everything.

**Fix:** Clamp: `limit = min(int(request.args.get('limit', 50)), 500)`. Add `offset` parameter for pagination.

---

### 34. Dashboard Sorts Messages Every Render

**File:** `src/pages/Dashboard.tsx:19-21`

```tsx
const recentMessages = [...messages]
  .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
  .slice(0, 5);
```

Creates and sorts a new array on every render cycle.

**Fix:** Wrap in `useMemo(() => ..., [messages])`.

---

### 35. Mock Data Resets on Component Mount

**File:** `src/contexts/NetworkContext.tsx:173`

`useEffect` reinitializes mock peers and messages whenever `username` changes. Changing your username wipes all state.

**Fix:** Initialize mock data in a separate `useEffect` with `[]` dependency, or persist state.

---

### 36. Missing Accessibility Labels

**Files:** `src/components/Layout.tsx:91,115`, `src/pages/Chat.tsx:315,322,348`

Interactive elements (menu buttons, send button, file attach button, message textarea) lack `aria-label` attributes.

**Fix:** Add descriptive `aria-label` to all interactive elements. Use semantic HTML (`<button>`, `<nav>`) instead of styled `<div>`s.

---

### 37. No Keyboard Navigation for Custom Components

**Files:** `src/pages/Dashboard.tsx`, `src/pages/Chat.tsx`, `src/pages/SSH.tsx`

Stat cards, quick actions, and peer lists are `<div>` elements. Not reachable via keyboard.

**Fix:** Use `<button>` or `<a>` for interactive items, or add `role="button"`, `tabIndex={0}`, and `onKeyDown` handlers.

---

### 38. SSH Component Mock Data on Every Mount

**File:** `src/pages/SSH.tsx:38-61`

Mock connections are recreated each time the SSH page mounts. Never cleaned up.

**Fix:** Move SSH connection state to `SSHContext`. Initialize once.

---

### 39. Weak Username Generation

**File:** `src/contexts/NetworkContext.tsx:50-52`

```typescript
`User_${Math.floor(Math.random() * 10000)}`
```

Only 10,000 possible default usernames. Collisions likely on busy networks.

**Fix:** Use `crypto.randomUUID().slice(0, 8)` or a word-based generator.

---

### 40. run.sh Deletes .venv Without Warning

**File:** `run.sh:39`

```bash
rm -rf .venv  # if pip is missing from existing venv
```

Silently destroys the virtual environment. User may have installed extra packages.

**Fix:** Warn the user and ask for confirmation, or try to repair the venv first.

---

### 41. run.sh Uses `--break-system-packages`

**File:** `run.sh:52`

```bash
python -m ensurepip --upgrade --break-system-packages
```

PEP 668 hack that can corrupt system Python on Kali/Debian.

**Fix:** Use `python3 -m venv` (with `python3-venv` package) instead of breaking system packages.

---

### 42. npm Install Only Runs When node_modules Missing

**File:** `run.sh:627-629`

Doesn't detect changes to `package.json` or `package-lock.json`. Users get stale dependencies.

**Fix:** Compare `package-lock.json` mtime against `node_modules/.package-lock.json` mtime, or always use `npm ci`.

---

### 43. Thread Never Joined in SSH Client UI

**File:** `ui/ssh_client.py:69-79`

Background connect threads are stored but never `.join()`ed. On app exit, threads are killed mid-operation.

**Fix:** Track threads and join them in cleanup. Set reasonable timeouts.

---

### 44. Unbounded Terminal History

**File:** `ui/terminal_widget.py:57`

```python
self.history_lines: List[str] = []
```

Terminal history grows without limit. Long SSH sessions will consume increasing memory.

**Fix:** Cap at 10,000 lines. Use `collections.deque(maxlen=10000)`.

---

### 45. Notification Weak Reference List Never Cleaned

**File:** `ui/notification.py:145`

Dead `weakref` entries accumulate in `_active_notifications`. The list grows with garbage references.

**Fix:** Periodically filter out dead refs, or use `weakref.WeakSet`.

---

### 46. No Error Handling in UI Callbacks

**Files:** `ui/chat_window.py:62-73`, `ui/terminal_widget.py:120-125`

Callbacks passed to UI components can raise exceptions that crash the entire GUI.

**Fix:** Wrap all callback invocations in try/except with error logging.

---

### 47. TypeScript Path Aliases May Break in Electron

**File:** `tsconfig.json:23-29`

`@/*` and `@components/*` aliases work via webpack in React but aren't resolved in Electron's main process.

**Fix:** Add a separate `tsconfig.electron.json` or avoid aliases in Electron-facing code.

---

### 48. Duplicate Color Definitions

**Files:** `ui/chat_window.py:138-152`, `ui/config.py:10-74`

Theme colors are hardcoded in both files.

**Fix:** Import colors from `config.py` only. Remove duplicates from `chat_window.py`.

---

### 49. No CSRF Protection

**File:** `src/services/api.ts`

POST/DELETE requests carry no CSRF token. If auth is added later, CSRF attacks become possible.

**Fix:** Implement CSRF tokens in Flask (`flask-wtf`) and send them via axios default headers.

---

### 50. Unused npm Dependencies

**File:** `package.json`

`react-beautiful-dnd`, `chart.js`, and `react-chartjs-2` are listed but not imported anywhere in `src/`.

**Fix:** Remove them to reduce install size and attack surface.

---

## Low

### 51. No `prefers-reduced-motion` Respect

**File:** `src/contexts/ThemeContext.tsx:24`

Smooth scroll animations play regardless of OS accessibility settings.

**Fix:** Check `window.matchMedia('(prefers-reduced-motion: reduce)')` before animating.

---

### 52. Hardcoded DHCP Defaults

**File:** `core/dhcp_server.py:56`

Network `192.168.100.0/24` and DNS `8.8.8.8` are hardcoded. Not configurable without code changes.

**Fix:** Read from `~/.ztalk/config.json` or accept parameters in the constructor.

---

### 53. No Audit Logging for SSH

**Files:** `core/ssh_manager.py`, `app.py`

SSH connection attempts, successes, and failures aren't logged with source IP or timestamp.

**Fix:** Log (without credentials): `logger.info(f"SSH connect attempt to {host}:{port} by {username}")`.

---

### 54. Unused Theme Config Key

**File:** `core/application.py:573`

Config has `"theme": "dark"` but it's never read by any code.

**Fix:** Remove it, or implement theme syncing between frontend and backend.

---

### 55. DevTools Auto-Open in Development

**File:** `public/electron.js:48-51`

DevTools open automatically in dev mode. Could confuse non-developer users testing the app.

**Fix:** Only open DevTools when explicitly requested (e.g., via menu or shortcut).

---

### 56. No Node.js Version Check in run.sh

**File:** `run.sh:621-624`

Checks that `npm` exists but not the Node.js version. Old Node versions will fail silently.

**Fix:** Check `node --version` and require v14+.

---

### 57. No Trap Handler for Cleanup in run.sh

**File:** `run.sh:683`

If the script is interrupted, the venv may be left in a partial state.

**Fix:** Add `trap cleanup EXIT` to kill background processes and clean up temp files.

---

### 58. Password Lingers in React State

**File:** `src/pages/SSH.tsx:357`

SSH password stays in component state after form submission until component unmounts.

**Fix:** Clear the password field from state immediately after the connect request is sent.

---

### 59. Tailwind Content Path Incomplete

**File:** `tailwind.config.js:3-5`

Only scans `src/` and `public/index.html`. Custom classes in other HTML templates would be purged.

**Fix:** Add `"./public/**/*.html"` to the content array.

---

### 60. No `requirements-dev.txt`

**File:** project root

No separation between runtime and development dependencies. No linting, formatting, or type-checking tools listed.

**Fix:** Create `requirements-dev.txt` with `pytest`, `pytest-cov`, `black`, `flake8`, `mypy`.

---

### 61. Windows Registry Access Unvalidated

**File:** `utils/windows_utils.py:645-650`

Registry operations lack path validation. Malformed paths could write to unintended keys.

**Fix:** Validate registry key paths against an allowlist before writing.

---

### 62. NSIS Script Injection Risk

**File:** `utils/windows_utils.py:414-490`

File paths are interpolated into NSIS scripts without escaping. Paths with special characters could inject NSIS commands.

**Fix:** Escape or quote all interpolated paths in NSIS script generation.

---

## Recommended Fix Order

### Phase 1 — Security (Issues 1-10)
Lock down the attack surface. No auth + open CORS + shell injection = critical exposure.

### Phase 2 — Stability (Issues 11-28)
Fix crashes, resource leaks, and missing error handling so the app runs reliably.

### Phase 3 — Quality (Issues 29-50)
Thread safety, accessibility, UX polish, and build correctness.

### Phase 4 — Polish (Issues 51-62)
Audit logging, developer tooling, platform edge cases.
