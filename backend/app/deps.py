from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Role, User
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def _resolve_user(db: Session, raw_token: str | None) -> User | None:
    if not raw_token:
        return None
    user_id = decode_access_token(raw_token)
    if user_id is None:
        return None
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    raw_token = token or request.cookies.get(settings.cookie_name)
    user = _resolve_user(db, raw_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_optional_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    raw_token = token or request.cookies.get(settings.cookie_name)
    return _resolve_user(db, raw_token)


def require_moderator(user: User = Depends(get_current_user)) -> User:
    if user.role not in (Role.moderator, Role.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нужна роль модератора или администратора")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нужна роль администратора")
    return user
