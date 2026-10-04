"""Tkinter control panel for OmniLog.

Runs the capture engine on a background thread and marshals live
events into the UI through a queue, so the interface never blocks.
"""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import config as config_mod
from . import crypto as crypto_mod
from . import engine as engine_mod


def _open_folder(path):
    os.makedirs(path, exist_ok=True)
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform == "win32":
        os.startfile(path)  # noqa: S606 (local path only)
    else:
        subprocess.Popen(["xdg-open", path])


class ControlPanel(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OmniLog Control Panel")
        self.geometry("640x560")
        self.cfg = config_mod.load()
        self.fernet = (
            crypto_mod.load_or_create_key(self.cfg["key_file"])
            if self.cfg["encryption_enabled"]
            else None
        )
        self.engine = engine_mod.KeyEngine(
            log_dir=self.cfg["log_dir"], fernet=self.fernet, on_event=self._queue_event
        )
        self.events = queue.Queue()
        self._build_widgets()
        self.after(120, self._drain_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- layout ---------------------------------------------------------

    def _build_widgets(self):
        pad = {"padx": 10, "pady": 4}

        top = ttk.Frame(self)
        top.pack(fill="x", **pad)

        ttk.Label(top, text="Session name:").pack(side="left")
        self.name_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.name_var, width=28).pack(side="left", padx=6)
        self.start_btn = ttk.Button(top, text="Start", command=self._start)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = ttk.Button(top, text="Stop", command=self._stop, state="disabled")
        self.stop_btn.pack(side="left")

        status = ttk.Frame(self)
        status.pack(fill="x", **pad)
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(status, text="Status:").pack(side="left")
        ttk.Label(status, textvariable=self.status_var, font=("", 10, "bold")).pack(side="left")
        enc = "ON (Fernet/AES)" if self.fernet else "OFF"
        ttk.Label(status, text=f"   Encryption: {enc}").pack(side="left")

        ttk.Label(self, text="Live capture:").pack(anchor="w", **pad)
        self.live = tk.Text(self, height=10, state="disabled", wrap="word")
        self.live.pack(fill="both", expand=True, **pad)

        mid = ttk.Frame(self)
        mid.pack(fill="x", **pad)
        ttk.Button(mid, text="Open log folder", command=lambda: _open_folder(self.cfg["log_dir"])).pack(side="left")
        ttk.Button(mid, text="Refresh sessions", command=self._refresh_sessions).pack(side="left", padx=6)

        ttk.Label(self, text="Past sessions (double-click to view):").pack(anchor="w", **pad)
        self.session_list = tk.Listbox(self, height=6)
        self.session_list.pack(fill="x", **pad)
        self.session_list.bind("<Double-Button-1>", self._view_session)
        self._refresh_sessions()

    # -- actions ----------------------------------------------------------

    def _start(self):
        try:
            path = self.engine.start(self.name_var.get())
        except RuntimeError as exc:
            messagebox.showwarning("OmniLog", str(exc))
            return
        except Exception as exc:  # e.g. no display server for pynput
            messagebox.showerror("OmniLog", f"Could not start capture:\n{exc}")
            return
        self.status_var.set(f"Recording → {os.path.basename(path)}")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._append_live(f"--- session started: {os.path.basename(path)} ---\n")

    def _stop(self):
        self.engine.stop()
        self.status_var.set("Idle")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self._append_live("--- session stopped ---\n")
        self._refresh_sessions()

    def _queue_event(self, entry):
        self.events.put(entry)

    def _drain_events(self):
        try:
            while True:
                entry = self.events.get_nowait()
                self._append_live(self._format_entry(entry) + "\n")
        except queue.Empty:
            pass
        self.after(120, self._drain_events)

    @staticmethod
    def _format_entry(entry):
        ts = entry.get("ts", "")[11:19]  # HH:MM:SS
        if entry.get("type") == "char":
            return f"[{ts}] {entry.get('key', '')}"
        if entry.get("type") == "special":
            return f"[{ts}] <{entry.get('key', '')}>"
        return f"[{ts}] ({entry.get('event', '')})"

    def _append_live(self, text):
        self.live.config(state="normal")
        self.live.insert("end", text)
        self.live.see("end")
        self.live.config(state="disabled")

    def _refresh_sessions(self):
        self.session_list.delete(0, "end")
        self._session_paths = engine_mod.list_sessions(self.cfg["log_dir"])
        for path in self._session_paths:
            self.session_list.insert("end", os.path.basename(path))

    def _view_session(self, _event=None):
        sel = self.session_list.curselection()
        if not sel:
            return
        path = self._session_paths[sel[0]]
        try:
            header, entries = engine_mod.read_session(path, self.fernet)
        except Exception as exc:
            messagebox.showerror("OmniLog", f"Could not read session:\n{exc}")
            return
        viewer = tk.Toplevel(self)
        viewer.title(os.path.basename(path))
        viewer.geometry("560x420")
        text = tk.Text(viewer, wrap="word")
        text.pack(fill="both", expand=True, padx=8, pady=8)
        text.insert("end", f"Session: {header.get('session')}  started {header.get('started')}\n")
        text.insert("end", f"Encrypted: {header.get('encrypted')}  events: {len(entries)}\n")
        text.insert("end", "-" * 50 + "\n")
        for entry in entries:
            text.insert("end", self._format_entry(entry) + "\n")
        text.config(state="disabled")

    def _on_close(self):
        if self.engine.running:
            if not messagebox.askyesno("OmniLog", "A session is recording. Stop it and quit?"):
                return
            self.engine.stop()
        self.destroy()


def run():
    ControlPanel().mainloop()


if __name__ == "__main__":
    run()
