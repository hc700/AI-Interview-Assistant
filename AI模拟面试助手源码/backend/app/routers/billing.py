"""订阅计费：套餐查询、下单、扫码支付确认。"""
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, is_member
from ..models import PaymentOrder, SubscriptionPlan, User, UserSubscription
from ..schemas import OrderCreateIn

router = APIRouter(prefix="/api", tags=["billing"])

_PERIOD_DAYS = {"monthly": 30, "quarterly": 92, "yearly": 365}


@router.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    rows = (db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.status == 1)
            .order_by(SubscriptionPlan.sort).all())
    return [{"id": p.id, "plan_code": p.plan_code, "name": p.name,
             "period_type": p.period_type, "price": float(p.price),
             "original_price": float(p.original_price) if p.original_price else None,
             "description": p.description} for p in rows]


@router.post("/orders")
def create_order(data: OrderCreateIn,
                 user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    plan = db.get(SubscriptionPlan, data.plan_id)
    if not plan or plan.status != 1:
        raise HTTPException(400, "套餐不存在或已停售")
    order = PaymentOrder(order_no=f"IV{datetime.now():%Y%m%d%H%M%S}{uuid.uuid4().hex[:6].upper()}",
                         user_id=user.id, plan_id=plan.id, amount=plan.price,
                         pay_channel=data.pay_channel, status="pending")
    db.add(order)
    db.commit()
    db.refresh(order)
    return {"order_id": order.id, "order_no": order.order_no,
            "plan_name": plan.name, "amount": float(order.amount),
            "status": order.status}


@router.post("/orders/{order_id}/confirm-pay")
def confirm_pay(order_id: int, user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """扫码支付确认：用户使用微信/支付宝收款码完成付款后调用，
    将订单置为 paid 并开通订阅权益。

    说明：个人收款码无商户支付网关的异步回调，此处以用户主动确认作为
    到账依据；生产环境可在微信/支付宝商户平台接入回调或由管理后台核对后确认。
    """
    order = db.query(PaymentOrder).filter(PaymentOrder.id == order_id,
                                          PaymentOrder.user_id == user.id).first()
    if not order:
        raise HTTPException(404, "订单不存在")
    if order.status == "paid":
        raise HTTPException(400, "订单已支付，请勿重复提交")
    plan = db.get(SubscriptionPlan, order.plan_id)
    now = datetime.now()
    order.status = "paid"
    order.paid_at = now
    order.transaction_id = f"QR{uuid.uuid4().hex[:20].upper()}"

    # 叠加订阅：在现有有效订阅基础上顺延
    current = (db.query(UserSubscription)
               .filter(UserSubscription.user_id == user.id,
                       UserSubscription.status == "active",
                       UserSubscription.end_time > now)
               .order_by(UserSubscription.end_time.desc()).first())
    start = current.end_time if current else now
    days = _PERIOD_DAYS.get(plan.period_type, 30)
    sub = UserSubscription(user_id=user.id, plan_id=plan.id, order_id=order.id,
                           start_time=start, end_time=start + timedelta(days=days),
                           status="active", auto_renew=1)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {"ok": True, "subscription": {"plan_name": plan.name,
                                          "end_time": sub.end_time.strftime("%Y-%m-%d")}}


@router.get("/users/me/subscription")
def my_subscription(user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    now = datetime.now()
    sub = (db.query(UserSubscription)
           .filter(UserSubscription.user_id == user.id,
                   UserSubscription.status == "active",
                   UserSubscription.end_time > now)
           .order_by(UserSubscription.end_time.desc()).first())
    if not sub:
        return {"is_member": False}
    plan = db.get(SubscriptionPlan, sub.plan_id)
    return {"is_member": True, "plan_name": plan.name if plan else "-",
            "end_time": sub.end_time.strftime("%Y-%m-%d"),
            "auto_renew": bool(sub.auto_renew)}


@router.post("/users/me/subscription/cancel")
def cancel_subscription(user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    now = datetime.now()
    sub = (db.query(UserSubscription)
           .filter(UserSubscription.user_id == user.id,
                   UserSubscription.status == "active",
                   UserSubscription.end_time > now)
           .order_by(UserSubscription.end_time.desc()).first())
    if not sub:
        raise HTTPException(400, "当前没有有效订阅")
    sub.auto_renew = 0
    sub.status = "cancelled"  # 权益保留至到期（demo 直接置 cancelled）
    db.commit()
    return {"ok": True, "end_time": sub.end_time.strftime("%Y-%m-%d")}
