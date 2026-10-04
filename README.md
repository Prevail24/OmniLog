# OmniLog v2

A local keystroke session recorder with encrypted logs and a control panel.
Built for security education and authorized testing on your own machines.

## What's new in v2

- **Control panel UI** — start/stop sessions, watch a live capture feed, and
  browse past sessions without touching the terminal.
- **Encrypted logs** — every session file is encrypted at rest with
  Fernet (AES-128-CBC + HMAC). The key is generated on first run and stored
  with owner-only permissions (`omnillog.key`). Guard that file: it decrypts
  everything.
- **Structured sessions** — one `.olog` file per session with a metadata
  header and one JSON event per line (timestamps, char vs. special keys).
- **Config file** — `config.json` controls the log folder, encryption, key
  location, and default session naming.
- **CLI mode** — the original headless behavior is still there, improved:
  `python main.py --cli` (Esc or Ctrl+C stops).

## Setup

1. Install Python 3.x.
2. Install dependencies: `pip install -r requirements.txt`
   - `pynput` — keyboard listener
   - `cryptography` — Fernet encryption
3. Run it: `python main.py`

On macOS, grant the terminal/IDE **Input Monitoring** permission when asked,
or the listener can't see keystrokes. On Linux, pynput needs an X session.

## Project layout

```
main.py              # entry point: UI by default, --cli for headless
config.json          # created on first run; edit to taste
omnillog/
  config.py          # load/save settings
  crypto.py          # Fernet key management + per-line encrypt/decrypt
  engine.py          # threaded capture engine + session read/write
  ui.py              # tkinter control panel
logs/                # session files (*.olog)
tests/
  test_core.py       # config/crypto/engine tests (no display needed)
```

## Config reference (`config.json`)

| Key | Default | Meaning |
|---|---|---|
| `log_dir` | `logs` | Where session files are written |
| `encryption_enabled` | `true` | Encrypt session contents at rest |
| `key_file` | `omnillog.key` | Fernet key location (mode 0600) |
| `session_prefix` | `session` | Used when no session name is given |

## Session file format

Line 1 is a plaintext header (metadata only, no keystroke content):

```json
{"format": "omnillog-v1", "encrypted": true, "session": "demo", "started": "..."}
```

Every following line is one event. With encryption on, each line is a
Fernet token; with it off, plain JSON:

```json
{"ts": "2026-10-03T20:00:00+00:00", "type": "char", "key": "h"}
{"ts": "2026-10-03T20:00:01+00:00", "type": "special", "key": "enter"}
{"ts": "2026-10-03T20:00:02+00:00", "type": "session", "event": "stop"}
```

Use `omnillog.engine.read_session(path, fernet)` to load one programmatically.

## A note on use

This is a learning tool. Only run it on machines you own or where you have
explicit permission to capture input. Keystroke data is sensitive — treat
the key file and the `logs/` folder accordingly.
