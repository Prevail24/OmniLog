"""Key-capture engine: a threaded listener writing structured session files.

Each session is one `.olog` file:

    {"format": "omnillog-v1", "encrypted": true, "session": "...", "started": "..."}
    <one JSON object per key event, encrypted per-line when enabled>
    {"ts": "...", "type": "session", "event": "stop"}

pynput is imported lazily inside start() so the rest of the module
(config, crypto, session reading) stays usable on machines without a
display server.
"""
import json
import os
import threading
from datetime import datetime, timezone

FORMAT = "omnillog-v1"


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


class KeyEngine:
    """Records key events to a session file. Safe to drive from a UI thread."""

    def __init__(self, log_dir="logs", fernet=None, on_event=None):
        self.log_dir = log_dir
        self.fernet = fernet
        self.on_event = on_event  # called with each entry dict (listener thread!)
        self.running = False
        self.session_name = None
        self.session_path = None
        self._listener = None
        self._keyboard = None
        self._file = None
        self._lock = threading.Lock()

    # -- lifecycle -----------------------------------------------------

    def start(self, session_name=None):
        """Begin a new session. Raises RuntimeError if already recording."""
        with self._lock:
            if self.running:
                raise RuntimeError("engine is already recording")
            from pynput import keyboard  # lazy: needs a display server

            self._keyboard = keyboard
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_name = (session_name or "").strip() or f"session_{ts}"
            # Sanitize: keep the filename filesystem-friendly.
            safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in self.session_name)
            self.session_path = os.path.join(self.log_dir, f"{safe}_{ts}.olog")
            os.makedirs(self.log_dir, exist_ok=True)
            self._file = open(self.session_path, "a", encoding="utf-8")
            header = {
                "format": FORMAT,
                "encrypted": self.fernet is not None,
                "session": self.session_name,
                "started": _now_iso(),
            }
            self._file.write(json.dumps(header) + "\n")
            self._file.flush()
            self._write_raw({"ts": _now_iso(), "type": "session", "event": "start"})
            self._listener = keyboard.Listener(
                on_press=self._on_press, on_release=self._on_release
            )
            self._listener.start()
            self.running = True
        return self.session_path

    def stop(self):
        """End the current session, idempotent."""
        with self._lock:
            if not self.running:
                return
            self.running = False
            listener, self._listener = self._listener, None
            try:
                self._write_raw({"ts": _now_iso(), "type": "session", "event": "stop"})
            finally:
                if self._file:
                    self._file.close()
                    self._file = None
            if listener is not None:
                listener.stop()

    # -- listener callbacks (run on pynput's thread) -------------------

    def _on_press(self, key):
        try:
            entry = {"ts": _now_iso(), "type": "char", "key": key.char}
        except AttributeError:
            name = str(key).split(".")[-1]  # Key.enter -> enter
            entry = {"ts": _now_iso(), "type": "special", "key": name}
        self.record(entry)

    def _on_release(self, key):
        # Esc stops the session even in headless/CLI mode.
        if self._keyboard is not None and key == self._keyboard.Key.esc:
            threading.Thread(target=self.stop, daemon=True).start()
            return False
        return None

    # -- recording ------------------------------------------------------

    def record(self, entry):
        """Write one entry dict to the session file (thread-safe)."""
        with self._lock:
            if not self.running or self._file is None:
                return
            self._write_raw(entry)
        if self.on_event is not None:
            try:
                self.on_event(entry)
            except Exception:
                pass  # UI callbacks must never break the recorder

    def _write_raw(self, entry):
        line = json.dumps(entry, ensure_ascii=False)
        if self.fernet is not None:
            line = self.fernet.encrypt(line.encode("utf-8")).decode("ascii")
        self._file.write(line + "\n")
        self._file.flush()


# -- session reading ----------------------------------------------------


def list_sessions(log_dir="logs"):
    """Return session file paths, newest first."""
    if not os.path.isdir(log_dir):
        return []
    files = [
        os.path.join(log_dir, name)
        for name in os.listdir(log_dir)
        if name.endswith(".olog")
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    return files


def read_session(path, fernet=None):
    """Return (header_dict, [entry_dict, ...]) for a session file.

    Pass the Fernet instance when the session is encrypted; raises
    InvalidToken if the key is wrong.
    """
    header = {}
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for i, raw in enumerate(f):
            line = raw.rstrip("\n")
            if not line:
                continue
            if i == 0:
                header = json.loads(line)
                continue
            if header.get("encrypted"):
                if fernet is None:
                    raise ValueError("session is encrypted but no key was provided")
                line = fernet.decrypt(line.encode("ascii")).decode("utf-8")
            entries.append(json.loads(line))
    return header, entries
