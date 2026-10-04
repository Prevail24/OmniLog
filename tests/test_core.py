"""Core tests for OmniLog v2. No display server or listener needed.

Run:  python tests/test_core.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omnillog import config, crypto, engine


def test_config_roundtrip(tmp):
    p = os.path.join(tmp, "config.json")
    cfg = config.load(p)  # creates with defaults
    assert cfg["encryption_enabled"] is True
    assert os.path.exists(p)
    cfg["log_dir"] = "mylogs"
    config.save(cfg, p)
    assert config.load(p)["log_dir"] == "mylogs"
    print("config roundtrip: OK")


def test_crypto_roundtrip(tmp):
    kf = os.path.join(tmp, "k.key")
    f1 = crypto.load_or_create_key(kf)
    assert oct(os.stat(kf).st_mode & 0o777) == "0o600", "key file must be owner-only"
    f2 = crypto.load_or_create_key(kf)  # reload path uses the same key
    token = crypto.encrypt_line(f1, '{"ts":"t","type":"char","key":"a"}')
    assert token != "a" and "\n" not in token
    assert crypto.decrypt_line(f2, token) == '{"ts":"t","type":"char","key":"a"}'
    print("crypto roundtrip: OK")


def _wire_file(eng, path, encrypted):
    """Open a session file on the engine without starting a live listener."""
    eng._file = open(path, "a", encoding="utf-8")
    eng._file.write(
        json.dumps(
            {"format": "omnillog-v1", "encrypted": encrypted,
             "session": "t", "started": "x"}
        )
        + "\n"
    )
    eng.running = True


def test_engine_encrypted(tmp):
    fernet = crypto.load_or_create_key(os.path.join(tmp, "k.key"))
    logdir = os.path.join(tmp, "logs")
    os.makedirs(logdir)
    eng = engine.KeyEngine(log_dir=logdir, fernet=fernet)
    path = os.path.join(logdir, "t.olog")
    _wire_file(eng, path, True)
    eng.record({"ts": "t1", "type": "char", "key": "a"})
    eng.record({"ts": "t2", "type": "special", "key": "enter"})
    eng.running = False
    eng._file.close()

    raw = open(path, encoding="utf-8").read()
    assert '"key": "a"' not in raw, "keystroke must not appear in plaintext"

    header, entries = engine.read_session(path, fernet)
    assert header["encrypted"] is True
    assert [e["key"] for e in entries] == ["a", "enter"]
    assert engine.list_sessions(logdir) == [path]
    print("engine encrypted write/read: OK")


def test_engine_plaintext(tmp):
    logdir = os.path.join(tmp, "logs")
    os.makedirs(logdir, exist_ok=True)
    eng = engine.KeyEngine(log_dir=logdir, fernet=None)
    path = os.path.join(logdir, "p.olog")
    _wire_file(eng, path, False)
    eng.record({"ts": "t1", "type": "char", "key": "z"})
    eng.running = False
    eng._file.close()

    header, entries = engine.read_session(path)
    assert header["encrypted"] is False
    assert entries[0]["key"] == "z"
    print("engine plaintext write/read: OK")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_config_roundtrip(tmp)
        test_crypto_roundtrip(tmp)
        test_engine_encrypted(tmp)
        test_engine_plaintext(tmp)
    print("All core tests passed.")


if __name__ == "__main__":
    main()
