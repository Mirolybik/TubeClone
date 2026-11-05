from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..metrics import metrics
from ..models import Role, Subscription, User, Video
from ..schemas import AuthOut, LoginIn, ProfileUpdate, RegisterIn, TokenOut
from ..security import create_access_token, hash_password, verify_password
from ..serializers import user_me

router = APIRouter(prefix="/api/auth", tags=["Аутентификация"])


def build_me(db: Session, user: User):
    videos_count = db.scalar(select(func.count(Video.id)).where(Video.owner_id == user.id)) or 0
    subscribers_count = db.scalar(select(func.count(Subscription.id)).where(Subscription.channel_id == user.id)) or 0
    subscriptions_count = (
        db.scalar(select(func.count(Subscription.id)).where(Subscription.subscriber_id == user.id)) or 0
    )
    return user_me(user, videos_count, subscribers_count, subscriptions_count)


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def authenticate(db: Session, login: str, password: str) -> User:
    user = db.scalar(select(User).where(or_(User.email == login.lower(), User.username == login)))
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт заблокирован")
    return user


@router.post("/register", response_model=AuthOut, status_code=status.HTTP_201_CREATED, summary="Регистрация")
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
    username = payload.username.strip()
    email = payload.email.lower().strip()
    existing = db.scalar(select(User).where(or_(User.email == email, User.username == username)))
    if existing is not None:
        detail = "Email уже занят" if existing.email == email else "Имя пользователя уже занято"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    is_first_user = (db.scalar(select(func.count(User.id))) or 0) == 0
    user = User(
        email=email,
        username=username,
        display_name=(payload.display_name or "").strip() or None,
        password_hash=hash_password(payload.password),
        role=Role.admin if is_first_user else Role.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    metrics.record_registration()

    set_auth_cookie(response, create_access_token(user))
    return AuthOut(user=build_me(db, user))


@router.post("/login", response_model=AuthOut, summary="Вход по email или username")
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    try:
        user = authenticate(db, payload.login.strip(), payload.password)
    except HTTPException:
        metrics.record_login(False)
        raise
    metrics.record_login(True)
    set_auth_cookie(response, create_access_token(user))
    return AuthOut(user=build_me(db, user))


@router.post("/token", response_model=TokenOut, summary="OAuth2 password flow (для Swagger)")
def token(response: Response, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = authenticate(db, form.username.strip(), form.password)
    except HTTPException:
        metrics.record_login(False)
        raise
    metrics.record_login(True)
    token_value = create_access_token(user)
    set_auth_cookie(response, token_value)
    return TokenOut(access_token=token_value)


@router.post("/logout", summary="Выход")
def logout(response: Response):
    response.delete_cookie(key=settings.cookie_name, path="/")
    return {"message": "Вы вышли из аккаунта"}


@router.get("/me", response_model=AuthOut, summary="Текущий пользователь")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AuthOut(user=build_me(db, user))


@router.patch("/me", response_model=AuthOut, summary="Обновить профиль")
def update_me(payload: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip() or None
    if payload.bio is not None:
        user.bio = payload.bio.strip() or None
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthOut(user=build_me(db, user))
