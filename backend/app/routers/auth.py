from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import Home, User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest
from app.utils.response import error_response, success_response


router = APIRouter(prefix="/auth", tags=["用户认证"])


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "home_id": user.home_id,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/register", summary="用户注册")
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == payload.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response("USERNAME_EXISTS", "用户名已存在"),
        )

    default_home = db.query(Home).order_by(Home.id.asc()).first()
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        nickname=payload.nickname,
        home_id=default_home.id if default_home else None,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return success_response(data=serialize_user(user), message="注册成功")


@router.post("/login", summary="用户登录")
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("UNAUTHORIZED", "用户名或密码错误"),
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_response("UNAUTHORIZED", "用户已停用"),
        )

    token = create_access_token(subject=str(user.id))
    return success_response(
        data={
            "access_token": token,
            "token_type": "bearer",
            "user": serialize_user(user),
        },
        message="登录成功",
    )


@router.get("/me", summary="获取当前用户")
def me(current_user: User = Depends(get_current_user)):
    return success_response(data=serialize_user(current_user))
