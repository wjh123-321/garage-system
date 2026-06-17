"""电子报价单 API - In-memory storage."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Optional


class QuotationItem(BaseModel):
    name: str
    quantity: int = 1
    unit_price: float
    total: Optional[float] = None


class QuotationCreate(BaseModel):
    customer_name: str
    customer_phone: str
    car_plate: str
    car_model: str = ""
    items: list[QuotationItem]
    notes: str = ""
    valid_days: int = 7


class QuotationItemResponse(BaseModel):
    name: str
    quantity: int
    unit_price: float
    total: float


class QuotationResponse(BaseModel):
    id: int
    quotation_no: str
    customer_name: str
    customer_phone: str
    car_plate: str
    car_model: str
    items: list[QuotationItemResponse]
    total_amount: float
    status: str
    notes: str
    valid_until: str
    created_at: str


router = APIRouter(prefix="/api/quotations", tags=["电子报价单"])

# In-memory storage
_store = []
_counter = 0


@router.post("", response_model=QuotationResponse, status_code=201)
def create_quotation(body: QuotationCreate):
    """创建电子报价单，生成报价编号并计算总金额。"""
    global _counter
    _counter += 1
    now = datetime.now()

    # 逐项计算小计
    items_data = []
    for item in body.items:
        total = item.total if item.total is not None else round(item.quantity * item.unit_price, 2)
        items_data.append({
            "name": item.name,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "total": total,
        })

    total_amount = round(sum(i["total"] for i in items_data), 2)

    # 报价编号: QJ-YYYYMMDD-XXX (QJ = 汽修报价)
    date_str = now.strftime("%Y%m%d")
    quotation_no = f"QJ-{date_str}-{_counter:03d}"

    # 有效期
    valid_until = (now + timedelta(days=body.valid_days)).strftime("%Y-%m-%d")

    record = {
        "id": _counter,
        "quotation_no": quotation_no,
        "customer_name": body.customer_name,
        "customer_phone": body.customer_phone,
        "car_plate": body.car_plate,
        "car_model": body.car_model,
        "items": items_data,
        "total_amount": total_amount,
        "status": "draft",
        "notes": body.notes,
        "valid_until": valid_until,
        "created_at": now.isoformat(),
    }
    _store.append(record)
    return record


@router.get("/{quotation_id}", response_model=QuotationResponse)
def get_quotation(quotation_id: int):
    """根据报价单 ID 查询报价详情。"""
    for q in _store:
        if q["id"] == quotation_id:
            return q
    raise HTTPException(status_code=404, detail="报价单不存在")


@router.get("", response_model=list[QuotationResponse])
def list_quotations():
    """返回所有报价单（按创建时间倒序）。"""
    return list(reversed(_store))
