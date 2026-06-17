"""Service reminder API router."""

import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..database import get_db
from ..models.customer import Customer
from ..models.reminder import ServiceReminder
from ..schemas.reminder import (
    ReminderCreate,
    ReminderUpdate,
    ReminderResponse,
    ReminderListResponse,
)

router = APIRouter(prefix="/api/reminders", tags=["服务提醒"])


def _to_response(r: ServiceReminder) -> ReminderResponse:
    customer = r.customer
    return ReminderResponse(
        id=r.id,
        customer_id=r.customer_id,
        car_plate=r.car_plate,
        reminder_type=r.reminder_type,
        title=r.title,
        description=r.description,
        last_service_date=r.last_service_date,
        next_service_date=r.next_service_date,
        mileage_remind=r.mileage_remind,
        is_notified=r.is_notified,
        is_active=r.is_active,
        created_at=r.created_at,
        updated_at=r.updated_at,
        customer_name=customer.name if customer else "",
        customer_phone=customer.phone if customer else "",
    )


@router.get("", response_model=ReminderListResponse)
def list_reminders(
    reminder_type: str = Query("", description="按类型筛选"),
    due_soon: bool = Query(False, description="仅显示即将到期(7天内)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询提醒列表，支持到期提醒筛选"""
    q = db.query(ServiceReminder).options(joinedload(ServiceReminder.customer))
    q = q.filter(ServiceReminder.is_active == True)

    if reminder_type:
        q = q.filter(ServiceReminder.reminder_type == reminder_type)
    if due_soon:
        now = datetime.datetime.now(datetime.timezone.utc)
        week_later = now + datetime.timedelta(days=7)
        q = q.filter(
            ServiceReminder.next_service_date.isnot(None),
            ServiceReminder.next_service_date.between(now, week_later),
            ServiceReminder.is_notified == False,
        )

    total = q.count()
    reminders = (
        q.order_by(ServiceReminder.next_service_date.asc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [_to_response(r) for r in reminders]
    return ReminderListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{reminder_id}", response_model=ReminderResponse)
def get_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """查询提醒详情"""
    r = (
        db.query(ServiceReminder)
        .options(joinedload(ServiceReminder.customer))
        .filter(ServiceReminder.id == reminder_id)
        .first()
    )
    if not r:
        raise HTTPException(404, "提醒不存在")
    return _to_response(r)


@router.post("", response_model=ReminderResponse, status_code=201)
def create_reminder(data: ReminderCreate, db: Session = Depends(get_db)):
    """创建服务提醒"""
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(400, "客户不存在")

    r = ServiceReminder(**data.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _to_response(r)


@router.put("/{reminder_id}", response_model=ReminderResponse)
def update_reminder(
    reminder_id: int, data: ReminderUpdate, db: Session = Depends(get_db)
):
    """更新提醒"""
    r = (
        db.query(ServiceReminder)
        .options(joinedload(ServiceReminder.customer))
        .filter(ServiceReminder.id == reminder_id)
        .first()
    )
    if not r:
        raise HTTPException(404, "提醒不存在")

    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return _to_response(r)


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: int, db: Session = Depends(get_db)):
    """删除提醒"""
    r = db.query(ServiceReminder).filter(ServiceReminder.id == reminder_id).first()
    if not r:
        raise HTTPException(404, "提醒不存在")
    db.delete(r)
    db.commit()
