from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.jwt import ( create_access_token,create_refresh_token,decode_token,hash_token )
from app.auth.password import hash_password, verify_password
from app.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


def _store_refresh_token(db: Session, user_id: int, token: str) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta( days=settings.REFRESH_TOKEN_EXPIRE_DAYS )
    db.add( RefreshToken( user_id=user_id, token_hash=hash_token(token),expires_at=expires_at ))


def register_user(db: Session, data: RegisterRequest) -> User:
    user = User( full_name=data.full_name.strip(), email=str(data.email).lower(),
                 phone=data.phone, hashed_password=hash_password(data.password), role="patient",
                 is_active=True )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException( status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists" )

    db.refresh(user)
    return user


def login_user(db: Session, data: LoginRequest) -> TokenResponse:
    user = ( db.query(User) .filter(User.email == str(data.email).lower()) .first() )

    if ( user is None or not user.is_active or not verify_password(data.password, user.hashed_password)):
        raise HTTPException( status_code=status.HTTP_401_UNAUTHORIZED, 
                             detail="Invalid email or password", 
                             headers={"WWW-Authenticate": "Bearer"})

    refresh_token = create_refresh_token(user.id)
    _store_refresh_token(db, user.id, refresh_token)
    db.commit()

    return TokenResponse( access_token=create_access_token(user.id, user.role), 
                          refresh_token=refresh_token )


def refresh_access_token(db: Session, token: str) -> str:
    invalid_token_error = HTTPException( status_code=status.HTTP_401_UNAUTHORIZED, 
                                         detail="Invalid or expired refresh token" )

    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        raise invalid_token_error

    subject = payload.get("sub")
    if payload.get("type") != "refresh" or not isinstance(subject, str):
        raise invalid_token_error

    try:
        user_id = int(subject)
    except ValueError:
        raise invalid_token_error

    stored_token = ( db.query(RefreshToken)
                    .filter( RefreshToken.user_id == user_id, 
                            RefreshToken.token_hash == hash_token(token), 
                            RefreshToken.revoked_at.is_(None) ) .first())

    if stored_token is None:
        raise invalid_token_error

    expires_at = stored_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= datetime.now(timezone.utc):
        raise invalid_token_error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise invalid_token_error

    return create_access_token(user.id, user.role)


def revoke_refresh_token(db: Session, token: str) -> None:
    invalid_token_error = HTTPException( status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token" )

    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        raise invalid_token_error

    subject = payload.get("sub")
    if payload.get("type") != "refresh" or not isinstance(subject, str):
        raise invalid_token_error

    try:
        user_id = int(subject)
    except ValueError:
        raise invalid_token_error

    stored_token = (
        db.query(RefreshToken)
        .filter( RefreshToken.user_id == user_id, RefreshToken.token_hash == hash_token(token),RefreshToken.revoked_at.is_(None))
        .first())

    if stored_token is None:
        raise invalid_token_error

    stored_token.revoked_at = datetime.now(timezone.utc)
    db.commit()