from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.user import User
from app.schemas.auth import ( AccessTokenResponse, AdminUserCreate, LoginRequest, RefreshTokenRequest,
                               RegisterRequest, TokenResponse )
from app.schemas.user import UserResponse
from app.services.auth_service import ( login_user, refresh_access_token, register_user, revoke_refresh_token )
from app.auth.password import hash_password
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post( "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED )
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    return register_user(db, payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return login_user(db, payload)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh( payload: RefreshTokenRequest,db: Session = Depends(get_db)) -> AccessTokenResponse:
    return AccessTokenResponse(access_token=refresh_access_token(db, payload.refresh_token))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout( payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> Response:
    revoke_refresh_token(db, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
def read_current_user( current_user: User = Depends(get_current_user)) -> User:
    return current_user

@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles("admin"))])
def create_staff_user(payload: AdminUserCreate, db: Session = Depends(get_db)) -> User:
    """Create an Admin or Doctor login. Public registration remains patient-only."""
    user = User(full_name=payload.full_name.strip(),
                email=str(payload.email).lower(),
                phone=payload.phone,
                hashed_password=hash_password(payload.password),
                role=payload.role,
                is_active=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")
    db.refresh(user)
    return user
