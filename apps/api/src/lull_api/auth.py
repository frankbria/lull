"""Auth router: email/pw signup + login, provider OAuth, and the current_user dependency.

ponytail: signup/login/oauth are thin handlers over security.py + the User table; no user service
layer for four endpoints. The 18+ gate is a single check at account creation (FR-A1).
"""

from __future__ import annotations

import uuid

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .oauth import OAuthError, OAuthVerifier, get_oauth_verifier
from .security import (
    create_access_token,
    create_guest_token,
    decode_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)

MIN_PASSWORD_LEN = 8


class SignupIn(BaseModel):
    email: str
    password: str
    age_confirmed: bool  # client attests 18+ (FR-A1)


class LoginIn(BaseModel):
    email: str
    password: str


class OAuthIn(BaseModel):
    id_token: str
    age_confirmed: bool = False  # only consulted when the OAuth login creates a new account


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GuestTokenOut(BaseModel):
    guest_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    age_verified: bool


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the bearer token to a User, or 401."""
    unauthorized = HTTPException(
        status_code=401, detail="not authenticated", headers={"WWW-Authenticate": "Bearer"}
    )
    if creds is None:
        raise unauthorized
    try:
        user_id = decode_access_token(creds.credentials)
    except jwt.InvalidTokenError:
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def current_user_optional(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Like current_user but returns None instead of raising — for guest-allowed endpoints."""
    if creds is None:
        return None
    try:
        user_id = decode_access_token(creds.credentials)
    except jwt.InvalidTokenError:
        return None
    return db.get(User, user_id)


@router.post("/signup", response_model=TokenOut, status_code=201)
def signup(body: SignupIn, db: Session = Depends(get_db)) -> TokenOut:
    if not body.age_confirmed:
        raise HTTPException(status_code=422, detail="must be 18 or older to create an account")
    if len(body.password) < MIN_PASSWORD_LEN:
        raise HTTPException(
            status_code=422, detail=f"password must be at least {MIN_PASSWORD_LEN} characters"
        )
    email = _normalize_email(body.email)
    if "@" not in email:
        raise HTTPException(status_code=422, detail="invalid email")
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="email already registered")

    user = User(email=email, password_hash=hash_password(body.password), age_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(User).where(User.email == _normalize_email(body.email)))
    # Same 401 whether the email is unknown or the password is wrong (no account enumeration).
    if (
        user is None
        or user.password_hash is None
        or not verify_password(body.password, user.password_hash)
    ):
        raise HTTPException(status_code=401, detail="invalid email or password")
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/oauth/{provider}", response_model=TokenOut)
def oauth(
    provider: str,
    body: OAuthIn,
    db: Session = Depends(get_db),
    verifier: OAuthVerifier = Depends(get_oauth_verifier),
) -> TokenOut:
    try:
        identity = verifier.verify(provider, body.id_token)
    except OAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    email = _normalize_email(identity.email)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        # First sign-in creates the account — still gated on the 18+ attestation.
        if not body.age_confirmed:
            raise HTTPException(status_code=422, detail="must be 18 or older to create an account")
        user = User(email=email, age_verified=True)  # oauth-only: no local password
        db.add(user)
        db.commit()
        db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id))


@router.post("/guest", response_model=GuestTokenOut)
def guest() -> GuestTokenOut:
    """Issue a signed guest identity so an unauthenticated client can claim its one free
    generation (FR-A2). Server-issued + integrity-protected — clients can't forge guest ids.
    ponytail: rotation abuse (minting many guest tokens) is bounded by IP rate-limiting at the
    edge, a deploy/infra concern — not solvable in the token itself."""
    token, _ = create_guest_token()
    return GuestTokenOut(guest_token=token)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, age_verified=user.age_verified)
