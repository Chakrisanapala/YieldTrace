"""
Authentication, User Management, and Role-Based Access Control (RBAC).

Roles:
1. Owner: Full administrative and executive access
2. Admin: System configuration, master data, user accounts
3. Salesman: Order creation, customer access (cannot alter costing or production)
4. Production Supervisor: Production runs, BOM execution, scrap recording
5. Accountant: GST billing, payments, receivables, invoices
6. Auditor: Read-only inspection of transactions, ledger, and forensics

Security:
- PBKDF2-HMAC-SHA256 password hashing with individual cryptographic salt (64 hex characters)
- Bearer session token management
- Role-based route authorization dependencies
"""
import hashlib
import os
import secrets
from datetime import datetime, timezone
from typing import Optional, List, Dict
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole, AuditLog


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """Hash a password using PBKDF2-HMAC-SHA256 with a unique salt."""
    if not salt:
        salt = secrets.token_hex(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    ).hex()
    return pwd_hash, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    """Verify a plain-text password against the stored PBKDF2 hash."""
    pwd_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(pwd_hash, password_hash)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole,
        full_name: Optional[str] = None
    ) -> User:
        """Register a new user account with hashed password and role."""
        existing = self.db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            raise ValueError(f"User with username '{username}' or email '{email}' already exists.")

        pwd_hash, salt = hash_password(password)
        user = User(
            username=username,
            full_name=full_name or username.capitalize(),
            email=email,
            password_hash=pwd_hash,
            password_salt=salt,
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, username_or_email: str, password: str) -> Optional[User]:
        """Authenticate user credentials and issue a session token."""
        user = self.db.query(User).filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()
        if not user or not user.is_active:
            return None

        if not verify_password(password, user.password_hash, user.password_salt):
            return None

        # Issue new session token
        token = secrets.token_urlsafe(48)
        user.session_token = token
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(user)
        return user

    def logout(self, token: str) -> bool:
        """Invalidate the session token."""
        user = self.db.query(User).filter(User.session_token == token).first()
        if user:
            user.session_token = None
            self.db.commit()
            return True
        return False

    def get_user_by_token(self, token: str) -> Optional[User]:
        """Retrieve user associated with the session token."""
        if not token:
            return None
        return self.db.query(User).filter(User.session_token == token, User.is_active == True).first()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Dependency that extracts and validates the Bearer token."""
    if not authorization:
        # Fallback for demo: if no token is passed, allow system fallback or raise 401
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Header: Authorization: Bearer <token>"
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Use 'Bearer <token>'"
        )

    token = parts[1]
    auth_service = AuthService(db)
    user = auth_service.get_user_by_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token."
        )
    return user


def require_roles(allowed_roles: List[UserRole]):
    """Decorator dependency to enforce Role-Based Access Control."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != UserRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in allowed_roles]}, but user is '{current_user.role.value}'"
            )
        return current_user
    return role_checker
