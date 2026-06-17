"""Fleet finance API router — 车队收支管理."""

import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, select, and_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.fleet import FleetFinance

router = APIRouter(prefix="/api/fleet/finance", tags=["车队收支"])


@router.get("")
def list_fleet_finance(
    vehicle_id: int | None = Query(None, description="车辆ID"),
    start: str = Query("", description="开始日期 YYYY-MM-DD"),
    end: str = Query("", description="结束日期 YYYY-MM-DD"),
    type: str | None = Query(None, description="筛选: income/expense"),
    category: str | None = Query(None, description="筛选分类"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """收支明细列表，支持筛选和分页."""
    stmt = select(FleetFinance)

    conditions = []
    if vehicle_id is not None:
        conditions.append(FleetFinance.vehicle_id == vehicle_id)
    if start:
        conditions.append(FleetFinance.date >= datetime.date.fromisoformat(start))
    if end:
        conditions.append(FleetFinance.date <= datetime.date.fromisoformat(end))
    if type:
        conditions.append(FleetFinance.type == type)
    if category:
        conditions.append(FleetFinance.category == category)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # 总条数
    count_stmt = select(func.count()).select_from(FleetFinance)
    if conditions:
        count_stmt = count_stmt.where(and_(*conditions))
    total = db.execute(count_stmt).scalar() or 0

    # 分页排序
    stmt = stmt.order_by(FleetFinance.date.desc(), FleetFinance.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).scalars().all()

    items = [
        {
            "id": r.id,
            "vehicle_id": r.vehicle_id,
            "type": r.type,
            "category": r.category,
            "amount": float(r.amount),
            "date": r.date.isoformat(),
            "remark": r.remark,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/summary")
def fleet_finance_summary(
    vehicle_id: int | None = Query(None, description="车辆ID"),
    start: str = Query("", description="开始日期 YYYY-MM-DD"),
    end: str = Query("", description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """收支汇总：总收入、总支出、利润."""
    conditions = []
    if vehicle_id is not None:
        conditions.append(FleetFinance.vehicle_id == vehicle_id)
    if start:
        conditions.append(FleetFinance.date >= datetime.date.fromisoformat(start))
    if end:
        conditions.append(FleetFinance.date <= datetime.date.fromisoformat(end))

    # 收入合计
    income_stmt = select(
        func.coalesce(func.sum(FleetFinance.amount), 0)
    ).where(
        FleetFinance.type == "income"
    )
    if conditions:
        income_stmt = income_stmt.where(and_(*conditions))
    total_income = float(db.execute(income_stmt).scalar() or 0)

    # 支出合计
    expense_stmt = select(
        func.coalesce(func.sum(FleetFinance.amount), 0)
    ).where(
        FleetFinance.type == "expense"
    )
    if conditions:
        expense_stmt = expense_stmt.where(and_(*conditions))
    total_expense = float(db.execute(expense_stmt).scalar() or 0)

    # 按分类统计支出
    cat_conditions = [FleetFinance.type == "expense"]
    if conditions:
        cat_conditions.extend(conditions)
    category_rows = (
        db.query(
            FleetFinance.category,
            func.coalesce(func.sum(FleetFinance.amount), 0).label("total"),
        )
        .filter(and_(*cat_conditions))
        .group_by(FleetFinance.category)
        .all()
    )
    expense_by_category = {
        r.category: float(r.total) for r in category_rows
    }

    # 按分类统计收入
    inc_cat_conditions = [FleetFinance.type == "income"]
    if conditions:
        inc_cat_conditions.extend(conditions)
    income_category_rows = (
        db.query(
            FleetFinance.category,
            func.coalesce(func.sum(FleetFinance.amount), 0).label("total"),
        )
        .filter(and_(*inc_cat_conditions))
        .group_by(FleetFinance.category)
        .all()
    )
    income_by_category = {
        r.category: float(r.total) for r in income_category_rows
    }

    return {
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "profit": round(total_income - total_expense, 2),
        "expense_by_category": expense_by_category,
        "income_by_category": income_by_category,
    }


@router.post("")
def create_fleet_finance(
    vehicle_id: int,
    type: str,
    category: str,
    amount: Decimal,
    date: str,
    remark: str = "",
    db: Session = Depends(get_db),
):
    """创建一条收支记录.

    type: income / expense
    category: 运费 / 油费 / 维修 / 保险 / 其他
    """
    VALID_TYPES = {"income", "expense"}
    VALID_CATEGORIES = {"运费", "油费", "维修", "保险", "其他"}

    if type not in VALID_TYPES:
        raise HTTPException(400, f"type 必须为 {VALID_TYPES}")
    if category not in VALID_CATEGORIES:
        raise HTTPException(400, f"category 必须为 {VALID_CATEGORIES} 之一")

    try:
        record_date = datetime.date.fromisoformat(date)
    except (ValueError, TypeError):
        raise HTTPException(400, "date 格式必须为 YYYY-MM-DD")

    if amount <= 0:
        raise HTTPException(400, "amount 必须大于 0")

    record = FleetFinance(
        vehicle_id=vehicle_id,
        type=type,
        category=category,
        amount=amount,
        date=record_date,
        remark=remark,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "vehicle_id": record.vehicle_id,
        "type": record.type,
        "category": record.category,
        "amount": float(record.amount),
        "date": record.date.isoformat(),
        "remark": record.remark,
    }


@router.delete("/{record_id}")
def delete_fleet_finance(record_id: int, db: Session = Depends(get_db)):
    """删除一条收支记录."""
    record = db.get(FleetFinance, record_id)
    if not record:
        raise HTTPException(404, "记录不存在")
    db.delete(record)
    db.commit()
    return {"detail": "已删除"}
