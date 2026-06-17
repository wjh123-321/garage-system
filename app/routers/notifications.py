"""Notification (SMS) router — mock send + pending query."""

import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.customer import Customer
from ..models.reminder import ServiceReminder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["通知"])


# ── Schemas ─────────────────────────────────────────────

class SendNotificationRequest(BaseModel):
    """发送通知请求体"""
    reminder_id: int = Field(..., description="提醒ID")
    customer_id: int = Field(..., description="客户ID")
    channel: str = Field("sms", description="发送渠道: sms / email / wechat")


class SendNotificationResponse(BaseModel):
    """发送通知响应 — mock"""
    success: bool = True
    message_id: str
    channel: str
    to: str
    content: str
    sent_at: str


class PendingNotificationItem(BaseModel):
    """待发送提醒条目"""
    reminder_id: int
    customer_id: int
    customer_name: str
    customer_phone: str
    car_plate: str
    reminder_type: str
    title: str
    description: str
    next_service_date: Optional[str] = None
    mileage_remind: int


class PendingNotificationList(BaseModel):
    """待发送提醒列表"""
    items: list[PendingNotificationItem]
    total: int


# ── Helpers ─────────────────────────────────────────────

def _gen_message_id() -> str:
    """生成模拟消息ID"""
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"MOCK-{ts}"


def _build_sms_content(reminder: ServiceReminder) -> str:
    """根据提醒类型生成短信内容模板"""
    date_str = ""
    if reminder.next_service_date:
        date_str = reminder.next_service_date.strftime("%Y-%m-%d")

    templates = {
        "maintenance": (
            f"【汽修厂】尊敬的客户，您的车辆({reminder.car_plate})"
            f"即将到达保养期限（{date_str}），请及时到店保养。"
        ),
        "inspection": (
            f"【汽修厂】尊敬的客户，您的车辆({reminder.car_plate})"
            f"年检将于{date_str}到期，请及时办理。"
        ),
        "insurance": (
            f"【汽修厂】尊敬的客户，您的车辆({reminder.car_plate})"
            f"保险将于{date_str}到期，请及时续保。"
        ),
    }
    return templates.get(
        reminder.reminder_type,
        f"【汽修厂】尊敬的客户，您的车辆({reminder.car_plate})"
        f"有新的服务提醒：{reminder.title}",
    )


# ── Endpoints ───────────────────────────────────────────

@router.post("/send", response_model=SendNotificationResponse)
def send_notification(
    data: SendNotificationRequest,
    db: Session = Depends(get_db),
):
    """发送短信提醒（Mock，不真实调用短信API）

    根据reminder_id查找提醒，标记为已通知，
    返回模拟的发送结果。
    """
    customer = (
        db.query(Customer)
        .filter(Customer.id == data.customer_id)
        .first()
    )
    if not customer:
        raise HTTPException(404, "客户不存在")

    reminder = (
        db.query(ServiceReminder)
        .filter(
            ServiceReminder.id == data.reminder_id,
            ServiceReminder.customer_id == data.customer_id,
        )
        .first()
    )
    if not reminder:
        raise HTTPException(404, "提醒不存在")

    # 生成内容 & 标记已通知
    content = _build_sms_content(reminder)
    reminder.is_notified = True
    db.commit()

    logger.info(
        "Mock SMS sent: customer=%s phone=%s reminder=%s",
        customer.name, customer.phone, reminder.title,
    )

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return SendNotificationResponse(
        success=True,
        message_id=_gen_message_id(),
        channel=data.channel,
        to=customer.phone,
        content=content,
        sent_at=now,
    )


@router.get("/pending", response_model=PendingNotificationList)
def list_pending_notifications(
    customer_id: int = Query(..., description="客户ID"),
    db: Session = Depends(get_db),
):
    """查询指定客户的待发送提醒（未通知 & 启用中）"""
    reminders = (
        db.query(ServiceReminder)
        .options(joinedload(ServiceReminder.customer))
        .filter(
            ServiceReminder.customer_id == customer_id,
            ServiceReminder.is_notified == False,
            ServiceReminder.is_active == True,
        )
        .order_by(ServiceReminder.next_service_date.asc().nullslast())
        .all()
    )

    items = [
        PendingNotificationItem(
            reminder_id=r.id,
            customer_id=r.customer_id,
            customer_name=r.customer.name if r.customer else "",
            customer_phone=r.customer.phone if r.customer else "",
            car_plate=r.car_plate,
            reminder_type=r.reminder_type,
            title=r.title,
            description=r.description,
            next_service_date=r.next_service_date.isoformat() if r.next_service_date else None,
            mileage_remind=r.mileage_remind,
        )
        for r in reminders
    ]

    return PendingNotificationList(items=items, total=len(items))
