from cryptography.fernet import Fernet
import sys

def generate_key():
    """
    Generate a new encryption key.
    """
    return Fernet.generate_key().decode()

def encrypt_password(password: str, key: str) -> str:
    """
    Encrypt a password using a key.
    """
    cipher_suite = Fernet(key.encode())
    return cipher_suite.encrypt(password.encode()).decode()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python encrypt_password.py <password> <key>")
        sys.exit(1)

    password = sys.argv[1]
    key = sys.argv[2]
    encrypted_password = encrypt_password(password, key)
    print(f"Encrypted password: {encrypted_password}")