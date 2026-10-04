"""Configuration handling for OmniLog.

Settings live in config.json next to the project files. Everything is
relative to the current working directory, so run the app from the
project folder (the way the original logger.py worked).
"""
import json
import os

CONFIG_FILE = "config.json"

DEFAULTS = {
    # Folder where session files (*.olog) are written
    "log_dir": "logs",
    # Encrypt session contents at rest with Fernet (AES). Disable only for debugging.
    "encryption_enabled": True,
    # File holding the Fernet key. Created automatically on first run (mode 0600).
    "key_file": "omnillog.key",
    # Prefix used when a session name isn't supplied.
    "session_prefix": "session",
}


def load(path=CONFIG_FILE):
    """Return the effective config, creating config.json with defaults if missing."""
    cfg = dict(DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            cfg.update(loaded)
    else:
        save(cfg, path)
    return cfg


def save(cfg, path=CONFIG_FILE):
    """Persist the config dict as pretty-printed JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    return path
