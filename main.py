"""OmniLog v2 entry point.

    python main.py          # control panel UI
    python main.py --cli    # headless recorder (original behavior, improved)
"""
import argparse
import time

from omnillog import config as config_mod
from omnillog import crypto as crypto_mod
from omnillog import engine as engine_mod


def run_cli(session_name=""):
    cfg = config_mod.load()
    fernet = (
        crypto_mod.load_or_create_key(cfg["key_file"])
        if cfg["encryption_enabled"]
        else None
    )
    eng = engine_mod.KeyEngine(log_dir=cfg["log_dir"], fernet=fernet)
    path = eng.start(session_name)
    print(f"--- OmniLog recording to {path} ---")
    print("--- Press Esc or Ctrl+C to stop ---")
    try:
        while eng.running:
            time.sleep(0.2)
    except KeyboardInterrupt:
        eng.stop()
    print("--- Session stopped ---")


def main():
    parser = argparse.ArgumentParser(description="OmniLog v2")
    parser.add_argument("--cli", action="store_true", help="run headless (no UI)")
    parser.add_argument("--session", default="", help="session name (CLI mode)")
    args = parser.parse_args()
    if args.cli:
        run_cli(args.session)
    else:
        from omnillog import ui as ui_mod

        ui_mod.run()


if __name__ == "__main__":
    main()
