"""通用依赖：当前用户、会员判定、配额。"""
from datetime import datetime

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserSubscription, UserQuota
from .security import decode_token
from .config import FREE_MONTHLY_QUOTA


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    uid = decode_token(auth[7:])
    if not uid:
        raise HTTPException(401, "登录已过期，请重新登录")
    user = db.get(User, uid)
    if not user or user.status != 1:
        raise HTTPException(401, "账号不可用")
    return user


def is_member(db: Session, user_id: int) -> bool:
    now = datetime.now()
    sub = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "active",
            UserSubscription.end_time > now,
        )
        .first()
    )
    return sub is not None


def get_or_create_quota(db: Session, user_id: int) -> UserQuota:
    month = datetime.now().strftime("%Y-%m")
    quota = (
        db.query(UserQuota)
        .filter(UserQuota.user_id == user_id, UserQuota.quota_month == month)
        .first()
    )
    if not quota:
        quota = UserQuota(
            user_id=user_id, quota_month=month, used_count=0, quota_limit=FREE_MONTHLY_QUOTA)
        db.add(quota)
        db.commit()
        db.refresh(quota)
    return quota
