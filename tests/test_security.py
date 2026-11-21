"""
Unit tests for Authentication, Role-Based Access Control, and Security.
"""
import pytest
from app.models import UserRole
from app.modules.auth.service import AuthService, verify_password, hash_password


def test_password_hashing_and_verification(db_session):
    """Verify PBKDF2-HMAC-SHA256 password hashing with cryptographic salt."""
    raw_pass = "SecurePass@2026"
    pwd_hash, salt = hash_password(raw_pass)

    assert pwd_hash != raw_pass
    assert len(salt) == 64  # 32 bytes hex
    assert verify_password(raw_pass, pwd_hash, salt) is True
    assert verify_password("WrongPassword", pwd_hash, salt) is False


def test_role_based_user_creation_and_auth(db_session):
    """Verify user registration, roles, and session token generation."""
    auth = AuthService(db_session)
    user = auth.register_user(
        username="auditor_test",
        email="audit_test@yieldtrace.local",
        password="AuditPassword#1",
        role=UserRole.AUDITOR,
        full_name="Karthik Auditor"
    )

    assert user.id is not None
    assert user.role == UserRole.AUDITOR

    # Authenticate
    authenticated = auth.authenticate("auditor_test", "AuditPassword#1")
    assert authenticated is not None
    assert authenticated.session_token is not None
    assert len(authenticated.session_token) > 20

    # Test invalid password
    failed = auth.authenticate("auditor_test", "InvalidPass")
    assert failed is None
