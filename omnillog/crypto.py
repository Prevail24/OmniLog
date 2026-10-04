"""At-rest encryption for OmniLog session files.

Uses Fernet (AES-128 in CBC mode with HMAC) from the `cryptography`
package. Each log line is encrypted independently so a session file
remains append-friendly: the recorder can keep writing without
re-encrypting the whole file.
"""
import os

from cryptography.fernet import Fernet, InvalidToken

__all__ = ["load_or_create_key", "encrypt_line", "decrypt_line", "InvalidToken"]


def load_or_create_key(key_path):
    """Return a Fernet instance, generating and storing a key on first run.

    The key file is created with mode 0600 (owner read/write only).
    Guard this file: anyone holding it can decrypt your sessions.
    """
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            key = f.read().strip()
        # Validate early so a corrupt key file fails fast with a clear error.
        fernet = Fernet(key)
    else:
        key = Fernet.generate_key()
        # Write atomically-ish: create with restrictive perms from the start.
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, key)
        finally:
            os.close(fd)
        fernet = Fernet(key)
    return fernet


def encrypt_line(fernet, plaintext):
    """Encrypt one log line; returns an ASCII string safe to store per-line."""
    return fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_line(fernet, token):
    """Reverse encrypt_line. Raises InvalidToken if the key is wrong or data tampered."""
    return fernet.decrypt(token.encode("ascii")).decode("utf-8")
