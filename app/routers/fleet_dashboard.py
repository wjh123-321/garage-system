"""Fleet dashboard API router -- 车队看板数据聚合."""

import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.fleet import FleetFinance
from ..models.reminder import ServiceReminder
from .fleet_vehicles import _vehicles

router = APIRouter(prefix="/api/fleet", tags=["车队看板"])


@router.get("/dashboard")
def fleet_dashboard(db: Session = Depends(get_db)):
    """车队看板：返回车辆、维修、保养、财务等汇总数据."""
    now = datetime.datetime.now(datetime.timezone.utc)
    today = datetime.date.today()
    month_start = today.replace(day=1)

    # 1. 总车辆数
    total_vehicles = len(_vehicles)

    # 2. 运行中
    active = sum(1 for v in _vehicles if v.get("status") == "运行")

    # 3. 维修中
    maintenance = sum(1 for v in _vehicles if v.get("status") == "维修")

    # 4. 待保养车辆数（保养提醒已到期）
    due_maintenance = (
        db.query(func.count(ServiceReminder.id))
        .filter(
            ServiceReminder.reminder_type == "maintenance",
            ServiceReminder.is_active == True,
            ServiceReminder.next_service_date.isnot(None),
            ServiceReminder.next_service_date <= now,
        )
        .scalar()
        or 0
    )

    # 5. 年检到期数（年检提醒已到期）
    due_inspection = (
        db.query(func.count(ServiceReminder.id))
        .filter(
            ServiceReminder.reminder_type == "inspection",
            ServiceReminder.is_active == True,
            ServiceReminder.next_service_date.isnot(None),
            ServiceReminder.next_service_date <= now,
        )
        .scalar()
        or 0
    )

    # 6. 本月总支出
    month_expense = (
        db.query(func.coalesce(func.sum(FleetFinance.amount), 0))
        .filter(
            FleetFinance.type == "expense",
            FleetFinance.date >= month_start,
            FleetFinance.date <= today,
        )
        .scalar()
        or 0
    )

    # 7. 本月油费
    month_fuel = (
        db.query(func.coalesce(func.sum(FleetFinance.amount), 0))
        .filter(
            FleetFinance.type == "expense",
            FleetFinance.category == "油费",
            FleetFinance.date >= month_start,
            FleetFinance.date <= today,
        )
        .scalar()
        or 0
    )

    return {
        "total_vehicles": total_vehicles,
        "active": active,
        "maintenance": maintenance,
        "due_maintenance": due_maintenance,
        "due_inspection": due_inspection,
        "month_expense": round(float(month_expense), 2),
        "month_fuel": round(float(month_fuel), 2),
    }
