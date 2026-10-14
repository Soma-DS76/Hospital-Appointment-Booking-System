from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import decode_token
from app.auth.oauth2 import oauth2_scheme
from app.database import get_db
from app.models.user import User


def get_current_user( token: str = Depends(oauth2_scheme), db: Session = Depends(get_db) ) -> User:
    credentials_error = HTTPException( status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token",
                                      headers={"WWW-Authenticate": "Bearer"})

    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        raise credentials_error

    subject = payload.get("sub")
    if payload.get("type") != "access" or not isinstance(subject, str):
        raise credentials_error

    try:
        user_id = int(subject)
    except ValueError:
        raise credentials_error

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_error

    return user


def require_roles(*roles: str) -> Callable[..., User]:
    def role_guard( current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException( status_code=status.HTTP_403_FORBIDDEN,detail="You do not have permission to perform this action")
        return current_user

    return role_guard