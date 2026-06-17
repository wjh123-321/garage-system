"""经营报表路由."""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.work_order import WorkOrder

_CN_MONTHS = [
    "", "1月", "2月", "3月", "4月", "5月", "6月",
    "7月", "8月", "9月", "10月", "11月", "12月",
]

router = APIRouter(prefix="/api/reports", tags=["经营报表"])


def _build_report(db: Session, start: datetime, end: datetime) -> dict:
    """查询指定时间范围内的经营数据."""
    row = (
        db.query(
            func.coalesce(func.sum(WorkOrder.total_amount), 0).label("total_revenue"),
            func.count(WorkOrder.id).label("order_count"),
        )
        .filter(WorkOrder.created_at >= start, WorkOrder.created_at < end)
        .first()
    )
    total_revenue = float(row.total_revenue)
    order_count = row.order_count
    avg_ticket = round(total_revenue / order_count, 2) if order_count else 0.0
    return {
        "total_revenue": total_revenue,
        "order_count": order_count,
        "avg_ticket": avg_ticket,
    }


@router.get("/daily")
def daily_report(
    date: date = Query(..., description="日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """日报：指定日期的工单营收、工单数、客单价."""
    start = datetime.combine(date, datetime.min.time())
    end = start + timedelta(days=1)
    report = _build_report(db, start, end)
    report["date"] = date.isoformat()
    return report


@router.get("/monthly")
def monthly_report(
    year: int = Query(..., ge=2000, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: Session = Depends(get_db),
):
    """月报：指定月份的工单营收、工单数、客单价."""
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    report = _build_report(db, start, end)
    report["date"] = f"{year}-{month:02d}"
    return report


@router.get("/summary")
def summary_report(db: Session = Depends(get_db)):
    """概况：累计工单营收、工单数、客单价."""
    row = (
        db.query(
            func.coalesce(func.sum(WorkOrder.total_amount), 0).label("total_revenue"),
            func.count(WorkOrder.id).label("order_count"),
        )
        .first()
    )
    total_revenue = float(row.total_revenue)
    order_count = row.order_count
    avg_ticket = round(total_revenue / order_count, 2) if order_count else 0.0
    return {
        "total_revenue": total_revenue,
        "order_count": order_count,
        "avg_ticket": avg_ticket,
        "date": "all",
    }


def _period_label(start: date, end: date) -> str:
    """生成中文期间标签."""
    # 整月
    if start.day == 1 and (end - start).days in (28, 29, 30, 31):
        return f"{start.year}年{_CN_MONTHS[start.month]}"
    return f"{start.isoformat()}~{end.isoformat()}"


def _build_compare_report(db: Session, start: date, end: date) -> dict:
    """生成单个期间的报表."""
    s = datetime.combine(start, datetime.min.time())
    e = datetime.combine(end, datetime.min.time())
    data = _build_report(db, s, e)
    return {
        "period": _period_label(start, end),
        "revenue": data["total_revenue"],
        "orders": data["order_count"],
        "avg_ticket": data["avg_ticket"],
    }


@router.get("/compare")
def compare_report(
    start: date = Query(..., description="开始日期 YYYY-MM-DD"),
    end: date = Query(..., description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """经营对比：当前期间 vs 上一同样长度期间."""
    if end <= start:
        return {"error": "end 必须大于 start"}

    span = (end - start).days
    prev_start = start - timedelta(days=span)
    prev_end = start

    current = _build_compare_report(db, start, end)
    previous = _build_compare_report(db, prev_start, prev_end)

    def pct(curr: float, prev: float) -> float:
        if prev == 0:
            return 0.0
        return round((curr - prev) / prev * 100, 1)

    changes = {
        "revenue_percent": pct(current["revenue"], previous["revenue"]),
        "orders_percent": pct(current["orders"], previous["orders"]),
        "avg_ticket_percent": pct(current["avg_ticket"], previous["avg_ticket"]),
    }

    return {"current": current, "previous": previous, "changes": changes}
