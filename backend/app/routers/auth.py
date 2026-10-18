from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Profile, UserRole
from app.schemas import UserCreate, UserLogin, UserResponse, Token
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    # Enforce allowed roles
    role = user_in.role if user_in.role in (UserRole.STUDENT, UserRole.ADMIN) else UserRole.STUDENT

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        role=role,
        full_name=user_in.full_name or user_in.email.split("@")[0],
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Initialize empty profile for user
    profile = Profile(
        user_id=user.id,
        target_roles=[],
        skills=[],
    )
    db.add(profile)
    db.commit()

    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role, "email": user.email}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        email=user.email,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
