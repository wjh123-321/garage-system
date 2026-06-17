"""会员卡/次卡管理API - In-memory storage."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional

# ── Schemas ──────────────────────────────────────────────

class MembershipCreate(BaseModel):
    customer_id: int
    type: str = Field(..., pattern="^(会员卡|次卡)$", description="卡类型：会员卡/次卡")
    balance: float = Field(..., gt=0, description="余额（会员卡为金额，次卡为次数）")
    expire_date: str = Field(..., description="到期日 YYYY-MM-DD")

class MembershipUpdate(BaseModel):
    type: Optional[str] = Field(None, pattern="^(会员卡|次卡)$")
    balance: Optional[float] = Field(None, gt=0)
    expire_date: Optional[str] = None

class MembershipResponse(BaseModel):
    id: int
    customer_id: int
    type: str
    balance: float
    expire_date: str
    customer_name: str = ""
    customer_phone: str = ""
    created_at: str

# ── Router ───────────────────────────────────────────────

router = APIRouter(prefix="/api/memberships", tags=["会员卡/次卡"])

# In-memory storage
_store: list[dict] = []
_counter = 0


def _find(idx: int) -> dict | None:
    for m in _store:
        if m["id"] == idx:
            return m
    return None


# Simulated customer name lookup (shared in-memory dummy)
_customer_names: dict[int, str] = {}


def _enrich(m: dict) -> dict:
    m = dict(m)
    cid = m.get("customer_id", 0)
    m["customer_name"] = _customer_names.get(cid, f"客户{cid}")
    m["customer_phone"] = ""
    return m


@router.post("", response_model=MembershipResponse, status_code=201)
def create_membership(body: MembershipCreate):
    """创建会员卡/次卡"""
    global _counter
    _counter += 1
    now = datetime.now().isoformat()
    record = {
        "id": _counter,
        "customer_id": body.customer_id,
        "type": body.type,
        "balance": body.balance,
        "expire_date": body.expire_date,
        "created_at": now,
    }
    _store.append(record)
    return _enrich(record)


@router.get("", response_model=list[MembershipResponse])
def list_memberships(
    customer_id: int = Query(0, description="按客户ID筛选"),
    card_type: str = Query("", alias="type", description="按卡类型筛选"),
):
    """查询会员卡列表"""
    results = list(_store)
    if customer_id:
        results = [m for m in results if m["customer_id"] == customer_id]
    if card_type:
        results = [m for m in results if m["type"] == card_type]
    return [_enrich(m) for m in results]


@router.get("/{membership_id}", response_model=MembershipResponse)
def get_membership(membership_id: int):
    """查询单张卡"""
    m = _find(membership_id)
    if not m:
        raise HTTPException(404, "会员卡不存在")
    return _enrich(m)


@router.put("/{membership_id}", response_model=MembershipResponse)
def update_membership(membership_id: int, body: MembershipUpdate):
    """更新会员卡"""
    m = _find(membership_id)
    if not m:
        raise HTTPException(404, "会员卡不存在")

    update_data = body.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if v is not None:
            m[k] = v
    return _enrich(m)


@router.delete("/{membership_id}", status_code=204)
def delete_membership(membership_id: int):
    """删除会员卡"""
    m = _find(membership_id)
    if not m:
        raise HTTPException(404, "会员卡不存在")
    _store.remove(m)


# ── 额外：消耗接口（消费余额/次数） ────────────────

class ConsumeRequest(BaseModel):
    amount: float = Field(..., gt=0, description="消费金额/次数")


@router.post("/{membership_id}/consume", response_model=MembershipResponse)
def consume_membership(membership_id: int, body: ConsumeRequest):
    """消费会员卡余额或次卡次数"""
    m = _find(membership_id)
    if not m:
        raise HTTPException(404, "会员卡不存在")
    if m["balance"] < body.amount:
        raise HTTPException(400, f"余额不足: 当前{int(m['balance']) if m['type'] == '次卡' else m['balance']}{'次' if m['type'] == '次卡' else '元'}")
    m["balance"] -= body.amount
    return _enrich(m)


# ── 额外：充值接口 ────────────────────────────────

class RechargeRequest(BaseModel):
    amount: float = Field(..., gt=0, description="充值金额/次数")


@router.post("/{membership_id}/recharge", response_model=MembershipResponse)
def recharge_membership(membership_id: int, body: RechargeRequest):
    """充值会员卡余额或次卡次数"""
    m = _find(membership_id)
    if not m:
        raise HTTPException(404, "会员卡不存在")
    m["balance"] += body.amount
    return _enrich(m)
