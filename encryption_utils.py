import os
import stat
from cryptography.fernet import Fernet

KEY_FILE = os.path.join(os.path.dirname(__file__), 'secret.key')

def get_cipher():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        # Secure file creation with 0o600 permissions (read/write by owner only)
        # We use os.open to set permissions atomically on creation
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        # For cross-platform compatibility, handle Windows separately or use default python open with chmod
        try:
            fd = os.open(KEY_FILE, flags, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(key)
        except OSError:
            # Fallback for systems that might not support atomic creation with flags easily
            with open(KEY_FILE, 'wb') as f:
                f.write(key)
            os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
    else:
        # Enforce strict permissions on every access
        try:
            os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
        with open(KEY_FILE, 'rb') as f:
            key = f.read()
    return Fernet(key)

def encrypt_password(password: str) -> str:
    if not password:
        return ""
    cipher = get_cipher()
    return cipher.encrypt(password.encode('utf-8')).decode('utf-8')

def decrypt_password(encrypted_password: str) -> str:
    if not encrypted_password:
        return ""
    cipher = get_cipher()
    try:
        return cipher.decrypt(encrypted_password.encode('utf-8')).decode('utf-8')
    except Exception:
        return ""
