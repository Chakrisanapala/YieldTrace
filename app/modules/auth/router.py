"""
Authentication API endpoints for YieldTrace.
"""
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserRole
from app.modules.auth.service import AuthService, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username_or_email: str
    password: str


class RegisterUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole
    full_name: Optional[str] = None


class UserProfileResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    email: str
    role: str
    is_active: bool


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and obtain session bearer token."""
    auth_service = AuthService(db)
    user = auth_service.authenticate(payload.username_or_email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    return {
        "access_token": user.session_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role.value,
            "email": user.email
        }
    }


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout and revoke session token."""
    auth_service = AuthService(db)
    auth_service.logout(current_user.session_token)
    return {"message": "Successfully logged out"}


@router.get("/me")
def get_profile(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role.value,
        "is_active": current_user.is_active
    }


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    """List all registered system users."""
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role.value,
            "is_active": u.is_active
        }
        for u in users
    ]


@router.post("/users")
def create_user(payload: RegisterUserRequest, db: Session = Depends(get_db)):
    """Register a new user account."""
    auth_service = AuthService(db)
    try:
        user = auth_service.register_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            role=payload.role,
            full_name=payload.full_name
        )
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "message": "User created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
