"""AES Encryption Utility.

Implements AES-256-CBC encryption for securely storing per-device identifiers and
optional FCM device tokens in the database.

SECURITY CRITICAL: The AES encryption key is defined in `config.py` and must be:
- 32 bytes (256 bits) for AES-256
- Stored securely (environment variable / secret manager)
- Never committed to version control
"""
import base64
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding as sym_padding

# Import the encryption key from config
# This key is defined as a global variable at the top of config.py
from config import Config

# Global AES encryption configuration
AES_KEY = Config.AES_ENCRYPTION_KEY  # 32 bytes for AES-256
AES_BLOCK_SIZE = 128  # bits (16 bytes)


class AESEncryption:
    """AES-256-CBC encryption/decryption."""
    
    def __init__(self, key=None):
        """
        Initialize AES encryption with key
        
        Args:
            key: 32-byte encryption key (defaults to Config.AES_ENCRYPTION_KEY)
        """
        self.key = key or AES_KEY
        
        # Validate key length
        if len(self.key) != 32:
            raise ValueError(f"AES key must be exactly 32 bytes for AES-256. Got {len(self.key)} bytes.")
    
    def encrypt(self, plaintext: str) -> bytes:
        """
        Encrypt plaintext string using AES-256-CBC
        
        Args:
            plaintext: String to encrypt (FCM device token)
        
        Returns:
            bytes: Encrypted data (IV + ciphertext) ready for database storage
        
        Raises:
            ValueError: If plaintext is empty
            Exception: If encryption fails
        """
        if not plaintext:
            raise ValueError("Plaintext cannot be empty")
        
        try:
            # Convert plaintext to bytes
            plaintext_bytes = plaintext.encode('utf-8')
            
            # Generate random IV (Initialization Vector)
            iv = os.urandom(16)  # 16 bytes for AES
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend(),
            )
            encryptor = cipher.encryptor()
            
            # Apply PKCS7 padding
            padder = sym_padding.PKCS7(AES_BLOCK_SIZE).padder()
            padded_data = padder.update(plaintext_bytes) + padder.finalize()
            
            # Encrypt
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            
            # Prepend IV to ciphertext for storage
            # Format: [IV (16 bytes)][Ciphertext (variable)]
            encrypted_data = iv + ciphertext
            
            return encrypted_data
            
        except Exception as e:
            raise Exception(f"Encryption failed: {str(e)}")
    
    def decrypt(self, encrypted_data: bytes) -> str:
        """
        Decrypt encrypted data using AES-256-CBC
        
        Args:
            encrypted_data: Encrypted bytes (IV + ciphertext) from database
        
        Returns:
            str: Decrypted plaintext (FCM device token)
        
        Raises:
            ValueError: If encrypted_data is invalid
            Exception: If decryption fails
        """
        if not encrypted_data or len(encrypted_data) < 16:
            raise ValueError("Invalid encrypted data")
        
        try:
            # Extract IV and ciphertext
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(self.key),
                modes.CBC(iv),
                backend=default_backend(),
            )
            decryptor = cipher.decryptor()
            
            # Decrypt
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove PKCS7 padding
            unpadder = sym_padding.PKCS7(AES_BLOCK_SIZE).unpadder()
            plaintext_bytes = unpadder.update(padded_plaintext) + unpadder.finalize()
            
            # Convert to string
            plaintext = plaintext_bytes.decode('utf-8')
            
            return plaintext
            
        except Exception as e:
            raise Exception(f"Decryption failed: {str(e)}")
    
    def encrypt_to_base64(self, plaintext: str) -> str:
        """
        Encrypt and encode to base64 string (for JSON/text storage)
        
        Args:
            plaintext: String to encrypt
        
        Returns:
            str: Base64-encoded encrypted data
        """
        encrypted_bytes = self.encrypt(plaintext)
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    
    def decrypt_from_base64(self, encrypted_base64: str) -> str:
        """
        Decrypt from base64-encoded string
        
        Args:
            encrypted_base64: Base64-encoded encrypted data
        
        Returns:
            str: Decrypted plaintext
        """
        encrypted_bytes = base64.b64decode(encrypted_base64)
        return self.decrypt(encrypted_bytes)


# Singleton instance for global use
_aes_instance = None


def get_aes_encryptor() -> AESEncryption:
    """Get singleton AES encryption instance."""
    global _aes_instance
    if _aes_instance is None:
        _aes_instance = AESEncryption()
    return _aes_instance


# Convenience functions for direct use
def encrypt_fcm_token(token: str) -> bytes:
    """
    Encrypt FCM device token for database storage
    
    Args:
        token: FCM device token string
    
    Returns:
        bytes: Encrypted token ready for BLOB storage
    """
    return get_aes_encryptor().encrypt(token)


def decrypt_fcm_token(encrypted_token: bytes) -> str:
    """
    Decrypt FCM device token from database
    
    Args:
        encrypted_token: Encrypted token bytes from database
    
    Returns:
        str: Decrypted FCM token string
    """
    return get_aes_encryptor().decrypt(encrypted_token)


# Example usage and testing function
def test_encryption():
    """Test encryption/decryption functionality"""
    test_token = "dGVzdF9maXJlYmFzZV9kZXZpY2VfdG9rZW5fMTIzNDU2Nzg5MA=="
    
    print("Testing AES Encryption")
    print(f"Original token: {test_token}")
    
    # Encrypt
    encrypted = encrypt_fcm_token(test_token)
    print(f"Encrypted (hex): {encrypted.hex()}")
    print(f"Encrypted length: {len(encrypted)} bytes")
    
    # Decrypt
    decrypted = decrypt_fcm_token(encrypted)
    print(f"Decrypted token: {decrypted}")
    
    # Verify
    assert test_token == decrypted, "Encryption/Decryption failed!"
    print("✅ Encryption test passed!")
    
    return True


if __name__ == '__main__':
    # Run test when module is executed directly
    test_encryption()
