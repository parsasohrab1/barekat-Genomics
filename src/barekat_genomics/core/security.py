"""امنیت و رعایت HIPAA برای داده‌های PHI."""

import base64
import hashlib
import hmac
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from passlib.context import CryptContext

from barekat_genomics.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _derive_fernet_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode()).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_phi(plaintext: str) -> str:
    """رمزنگاری داده‌های محافظت‌شده سلامت (PHI)."""
    settings = get_settings()
    fernet = Fernet(_derive_fernet_key(settings.encryption_key))
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_phi(ciphertext: str) -> str:
    """رمزگشایی داده‌های PHI."""
    settings = get_settings()
    fernet = Fernet(_derive_fernet_key(settings.encryption_key))
    return fernet.decrypt(ciphertext.encode()).decode()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token_payload(user_id: str, role: str) -> dict:
    return {
        "sub": user_id,
        "role": role,
        "iat": datetime.now(timezone.utc).isoformat(),
    }


def anonymize_patient_id(patient_id: str, salt: str) -> str:
    """تولید شناسه ناشناس برای استفاده در تحلیل‌ها."""
    return hmac.new(salt.encode(), patient_id.encode(), hashlib.sha256).hexdigest()[:16]
