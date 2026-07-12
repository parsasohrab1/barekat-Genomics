"""Security utilities tests."""

from barekat_genomics.core.security import (
    encrypt_phi,
    decrypt_phi,
    hash_password,
    verify_password,
    anonymize_patient_id,
)


def test_phi_encryption_roundtrip():
    original = "احمد محمدی"
    encrypted = encrypt_phi(original)
    assert encrypted != original
    decrypted = decrypt_phi(encrypted)
    assert decrypted == original


def test_password_hashing():
    password = "secure-password-123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)


def test_anonymize_patient_id():
    anon1 = anonymize_patient_id("P0001", "salt")
    anon2 = anonymize_patient_id("P0001", "salt")
    anon3 = anonymize_patient_id("P0002", "salt")
    assert anon1 == anon2
    assert anon1 != anon3
    assert len(anon1) == 16
