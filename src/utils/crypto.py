import os
import base64
import logging
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

ENV_FILE = Path(".env")
KEY_VAR_NAME = "NAGROM_ENCRYPTION_KEY"

def get_or_create_key() -> bytes:
    """
    Retrieves the encryption key from environment or .env file.
    If it doesn't exist, generates a new one and saves it to .env.
    """
    key_str = os.getenv(KEY_VAR_NAME)
    
    if key_str:
        try:
            return base64.urlsafe_b64decode(key_str)
        except Exception:
            # If it's not base64, maybe it's raw bytes or a simple string we can derive from?
            # For safety, let's assume it should be a Fernet key (32 url-safe base64-encoded bytes).
            # If invalid, we might be in trouble for existing data, but here we are starting fresh or fixing.
            logger.warning("Invalid encryption key format in environment. Generating new one.")
            pass

    # Generate new key
    key = Fernet.generate_key()
    key_str = key.decode("utf-8")
    
    # Save to .env
    try:
        if ENV_FILE.exists():
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Check if key exists but was empty or we missed it
            key_exists = False
            new_lines = []
            for line in lines:
                if line.startswith(f"{KEY_VAR_NAME}="):
                    new_lines.append(f"{KEY_VAR_NAME}={key_str}\n")
                    key_exists = True
                else:
                    new_lines.append(line)
            
            if not key_exists:
                if new_lines and not new_lines[-1].endswith("\n"):
                    new_lines.append("\n")
                new_lines.append(f"{KEY_VAR_NAME}={key_str}\n")
            
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
        else:
            with open(ENV_FILE, "w", encoding="utf-8") as f:
                f.write(f"{KEY_VAR_NAME}={key_str}\n")
        
        # Set in current env for this session
        os.environ[KEY_VAR_NAME] = key_str
        logger.info(f"Generated and saved new encryption key to {ENV_FILE}")
        
    except Exception as e:
        logger.error(f"Failed to save encryption key to .env: {e}")
        # We still return the key to allow operation, but persistence will fail
        
    return key

class CryptoManager:
    _cipher_suite = None

    @classmethod
    def get_cipher(cls):
        if cls._cipher_suite is None:
            key = get_or_create_key()
            cls._cipher_suite = Fernet(key)
        return cls._cipher_suite

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        if not plaintext:
            return ""
        cipher = cls.get_cipher()
        return cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    @classmethod
    def decrypt(cls, ciphertext: str) -> str:
        if not ciphertext:
            return ""
        try:
            cipher = cls.get_cipher()
            return cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return ciphertext  # Return raw if decryption fails (backward compatibility or error)

