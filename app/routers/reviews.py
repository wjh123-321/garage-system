"""客户评价 API router — 内存模拟"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/reviews", tags=["客户评价"])

# ── 内存模拟存储 ──────────────────────────────────────────────
_reviews: list[dict] = []
_next_id = 1


# ── Schema ─────────────────────────────────────────────────────
class ReviewCreate(BaseModel):
    order_id: int = Field(..., description="工单ID")
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    comment: str = Field("", max_length=500, description="文字评价")


class ReviewResponse(BaseModel):
    id: int
    order_id: int
    rating: int
    comment: str
    created_at: str


# ── API ────────────────────────────────────────────────────────
@router.post("", response_model=ReviewResponse, summary="提交评价")
def create_review(body: ReviewCreate):
    global _next_id
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(400, "评分必须在 1-5 之间")
    record = {
        "id": _next_id,
        "order_id": body.order_id,
        "rating": body.rating,
        "comment": body.comment,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _next_id += 1
    _reviews.append(record)
    return record


@router.get("", response_model=list[ReviewResponse], summary="查询评价（按工单）")
def list_reviews(order_id: Optional[int] = Query(None, description="工单ID，不传返回全部")):
    if order_id is not None:
        return [r for r in _reviews if r["order_id"] == order_id]
    return _reviews
