"""Finance API router."""

import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, union_all, literal_column
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.work_order import WorkOrder
from ..models.part import InventoryTransaction

router = APIRouter(prefix="/api/finance", tags=["财务管理"])


@router.get("/overview")
def finance_overview(db: Session = Depends(get_db)):
    """财务总览：总营收、总支出、利润"""
    # 营收：已完成工单总金额
    revenue = (
        db.query(func.coalesce(func.sum(WorkOrder.total_amount), 0))
        .filter(WorkOrder.status == "completed")
        .scalar()
    )
    # 支出：入库采购总金额（数量 * 单价）
    expenditure = (
        db.query(
            func.coalesce(
                func.sum(InventoryTransaction.quantity * InventoryTransaction.unit_price), 0
            )
        )
        .filter(InventoryTransaction.type == "in")
        .scalar()
    )
    completed_count = (
        db.query(func.count(WorkOrder.id))
        .filter(WorkOrder.status == "completed")
        .scalar()
    )

    return {
        "total_revenue": round(float(revenue), 2),
        "total_expenditure": round(float(expenditure), 2),
        "profit": round(float(revenue) - float(expenditure), 2),
        "completed_orders_count": completed_count,
    }


@router.get("/transactions")
def finance_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """收支明细（收入 + 支出），按时间倒序分页返回"""
    # 收入：已完成工单
    revenue_stmt = select(
        literal_column("'income'").label("type"),
        literal_column("'work_order'").label("category"),
        WorkOrder.id.label("reference_id"),
        WorkOrder.order_no.label("reference_no"),
        WorkOrder.total_amount.label("amount"),
        WorkOrder.completed_at.label("date"),
    ).where(WorkOrder.status == "completed")

    # 支出：入库采购
    expense_stmt = select(
        literal_column("'expense'").label("type"),
        literal_column("'purchase'").label("category"),
        InventoryTransaction.id.label("reference_id"),
        literal_column("''").label("reference_no"),
        (InventoryTransaction.quantity * InventoryTransaction.unit_price).label("amount"),
        InventoryTransaction.created_at.label("date"),
    ).where(InventoryTransaction.type == "in")

    # UNION ALL + 排序
    union_stmt = union_all(revenue_stmt, expense_stmt).order_by(
        literal_column("date").desc()
    )
    union_alias = union_stmt.alias("u")

    # 总条数
    total = (
        db.execute(select(func.count()).select_from(union_alias)).scalar() or 0
    )

    # 分页
    paginated = (
        select(union_alias).offset((page - 1) * page_size).limit(page_size)
    )
    rows = db.execute(paginated).all()

    items = [
        {
            "type": r.type,
            "category": r.category,
            "reference_id": r.reference_id,
            "reference_no": r.reference_no,
            "amount": round(float(r.amount), 2),
            "date": r.date.isoformat() if r.date else None,
        }
        for r in rows
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/stats")
def finance_stats(
    start: str = Query("", description="开始日期 YYYY-MM-DD"),
    end: str = Query("", description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """财务统计：按日汇总营收/支出/利润"""
    today = datetime.date.today()
    start_date = datetime.date.fromisoformat(start) if start else today.replace(day=1)
    end_date = datetime.date.fromisoformat(end) if end else today

    # 每日营收（已完成工单）
    revenue_rows = (
        db.query(
            func.date(WorkOrder.completed_at).label("date"),
            func.coalesce(func.sum(WorkOrder.total_amount), 0).label("revenue"),
        )
        .filter(
            WorkOrder.status == "completed",
            WorkOrder.completed_at.isnot(None),
            func.date(WorkOrder.completed_at) >= start_date,
            func.date(WorkOrder.completed_at) <= end_date,
        )
        .group_by(func.date(WorkOrder.completed_at))
        .order_by(func.date(WorkOrder.completed_at))
        .all()
    )

    # 每日支出（入库采购）
    expense_rows = (
        db.query(
            func.date(InventoryTransaction.created_at).label("date"),
            func.coalesce(
                func.sum(
                    InventoryTransaction.quantity * InventoryTransaction.unit_price
                ),
                0,
            ).label("expenditure"),
        )
        .filter(
            InventoryTransaction.type == "in",
            func.date(InventoryTransaction.created_at) >= start_date,
            func.date(InventoryTransaction.created_at) <= end_date,
        )
        .group_by(func.date(InventoryTransaction.created_at))
        .order_by(func.date(InventoryTransaction.created_at))
        .all()
    )

    # 合并为按日 map
    daily_map: dict[str, dict] = {}
    for r in revenue_rows:
        d = r.date.isoformat() if r.date else str(r.date)
        daily_map[d] = {"revenue": round(float(r.revenue), 2), "expenditure": 0.0}

    for r in expense_rows:
        d = r.date.isoformat() if r.date else str(r.date)
        if d in daily_map:
            daily_map[d]["expenditure"] = round(float(r.expenditure), 2)
        else:
            daily_map[d] = {
                "revenue": 0.0,
                "expenditure": round(float(r.expenditure), 2),
            }

    # 计算利润并排序
    daily_list: list[dict] = []
    total_revenue = 0.0
    total_expenditure = 0.0
    for d in sorted(daily_map.keys()):
        entry = daily_map[d]
        entry["profit"] = round(entry["revenue"] - entry["expenditure"], 2)
        entry["date"] = d
        daily_list.append(entry)
        total_revenue += entry["revenue"]
        total_expenditure += entry["expenditure"]

    days = len(daily_list) or 1

    return {
        "daily": daily_list,
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_expenditure": round(total_expenditure, 2),
            "profit": round(total_revenue - total_expenditure, 2),
            "avg_daily_revenue": round(total_revenue / days, 2),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    }
