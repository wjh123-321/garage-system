"""Performance and technician statistics API router."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.work_order import WorkOrder

router = APIRouter(prefix="/api/performance", tags=["绩效统计"])


# ---------- response models ----------

class TechnicianSummary(BaseModel):
    technician: str
    order_count: int
    total_amount: float
    avg_amount: float


class TechnicianStats(BaseModel):
    technician: str
    order_count: int
    total_amount: float
    avg_amount: float
    completed_count: int
    cancelled_count: int
    pending_count: int
    in_progress_count: int
    period_start: str
    period_end: str


class RankingItem(BaseModel):
    rank: int
    technician: str
    order_count: int
    total_amount: float
    avg_amount: float


# ---------- helpers ----------

def _aggregate_technician(
    query,
) -> list[dict]:
    """Run a GROUP BY technician query and return aggregated rows."""
    rows = (
        query.with_entities(
            WorkOrder.technician,
            func.count(WorkOrder.id).label("order_count"),
            func.coalesce(func.sum(WorkOrder.total_amount), 0).label("total_amount"),
        )
        .group_by(WorkOrder.technician)
        .order_by(func.count(WorkOrder.id).desc())
        .all()
    )
    result = []
    for r in rows:
        if not r.technician:
            continue
        cnt = r.order_count
        amt = float(r.total_amount)
        result.append(
            {
                "technician": r.technician,
                "order_count": cnt,
                "total_amount": amt,
                "avg_amount": round(amt / cnt, 2) if cnt > 0 else 0.0,
            }
        )
    return result


# ---------- endpoints ----------


@router.get("/technicians", response_model=list[TechnicianSummary])
def list_technicians(db: Session = Depends(get_db)):
    """技师列表，返回每位技师的总工单数和总金额，按工单数降序排列。"""
    base = db.query(WorkOrder)
    return _aggregate_technician(base)


@router.get("/stats", response_model=TechnicianStats)
def technician_stats(
    tech_id: str = Query("", description="技师姓名"),
    start: str = Query("", description="开始日期 yyyy-mm-dd"),
    end: str = Query("", description="结束日期 yyyy-mm-dd"),
    db: Session = Depends(get_db),
):
    """指定技师的绩效统计，可筛选日期范围。"""
    if not tech_id:
        raise HTTPException(400, "tech_id (技师姓名) 必填")

    base = db.query(WorkOrder).filter(WorkOrder.technician == tech_id)

    if start:
        try:
            dt_start = datetime.datetime.strptime(start, "%Y-%m-%d")
            base = base.filter(WorkOrder.created_at >= dt_start)
        except ValueError:
            raise HTTPException(400, "start 格式错误，应为 yyyy-mm-dd")
    if end:
        try:
            # include the whole end day
            dt_end = datetime.datetime.strptime(end, "%Y-%m-%d") + datetime.timedelta(
                days=1
            )
            base = base.filter(WorkOrder.created_at < dt_end)
        except ValueError:
            raise HTTPException(400, "end 格式错误，应为 yyyy-mm-dd")

    row = (
        base.with_entities(
            func.count(WorkOrder.id).label("order_count"),
            func.coalesce(func.sum(WorkOrder.total_amount), 0).label("total_amount"),
        )
        .first()
    )

    cnt = row.order_count
    amt = float(row.total_amount)

    # status breakdown
    statuses = (
        base.with_entities(WorkOrder.status, func.count(WorkOrder.id))
        .group_by(WorkOrder.status)
        .all()
    )
    status_map = {s: c for s, c in statuses}

    return TechnicianStats(
        technician=tech_id,
        order_count=cnt,
        total_amount=amt,
        avg_amount=round(amt / cnt, 2) if cnt > 0 else 0.0,
        completed_count=status_map.get("completed", 0),
        cancelled_count=status_map.get("cancelled", 0),
        pending_count=status_map.get("pending", 0),
        in_progress_count=status_map.get("in_progress", 0),
        period_start=start or "全部",
        period_end=end or "全部",
    )


@router.get("/ranking", response_model=list[RankingItem])
def technician_ranking(db: Session = Depends(get_db)):
    """技师绩效排名，按工单数降序，附带总金额和均值。"""
    items = _aggregate_technician(db.query(WorkOrder))
    return [
        RankingItem(rank=i + 1, **item) for i, item in enumerate(items)
    ]
