from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, is_member
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserInfo
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "该邮箱已注册")
    user = User(email=data.email, nickname=data.nickname or data.email.split("@")[0],
                password_hash=hash_password(data.password), register_source="email",
                status=1, last_login_at=datetime.now())
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(token=create_token(user.id),
                    user=UserInfo(id=user.id, email=user.email, nickname=user.nickname))


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(400, "邮箱或密码错误")
    if user.status != 1:
        raise HTTPException(403, "账号已被禁用")
    user.last_login_at = datetime.now()
    db.commit()
    return TokenOut(token=create_token(user.id),
                    user=UserInfo(id=user.id, email=user.email, nickname=user.nickname))


@router.get("/me", response_model=UserInfo)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return UserInfo(id=user.id, email=user.email, phone=user.phone,
                    nickname=user.nickname, is_member=is_member(db, user.id))
