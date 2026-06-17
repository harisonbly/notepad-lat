from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import os

def derive_key(password, salt=None):
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000, backend=default_backend())
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt

def encrypt_data(data, password):
    key, salt = derive_key(password)
    cipher_suite = Fernet(key)
    encrypted = cipher_suite.encrypt(data.encode() if isinstance(data, str) else data)
    return base64.urlsafe_b64encode(salt + encrypted)

def decrypt_data(encrypted_data, password):
    encrypted_data = base64.urlsafe_b64decode(encrypted_data)
    salt = encrypted_data[:16]
    encrypted_content = encrypted_data[16:]
    key, _ = derive_key(password, salt)
    cipher_suite = Fernet(key)
    decrypted = cipher_suite.decrypt(encrypted_content)
    return decrypted.decode()
