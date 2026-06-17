"""接车验车单API - In-memory storage."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class InspectionCreate(BaseModel):
    order_id: int
    photos: list[dict] = []  # [{"angle": "前保险杠", "path": "temp_path"}, ...]
    notes: str = ""
    mileage: Optional[int] = None
    fuel_level: Optional[str] = None  # 油量: 满/3/4/半/1/4/少


class InspectionResponse(BaseModel):
    id: int
    order_id: int
    photos: list[dict]
    notes: str
    mileage: Optional[int] = None
    fuel_level: Optional[str] = None
    created_at: str
    updated_at: str


router = APIRouter(prefix="/api/inspection", tags=["接车验车"])

_store = []
_counter = 0


@router.post("", response_model=InspectionResponse, status_code=201)
def create_inspection(body: InspectionCreate):
    """保存验车记录."""
    global _counter
    _counter += 1
    now = datetime.now().isoformat()
    record = {
        "id": _counter,
        "order_id": body.order_id,
        "photos": body.photos,
        "notes": body.notes,
        "mileage": body.mileage,
        "fuel_level": body.fuel_level,
        "created_at": now,
        "updated_at": now,
    }
    _store.append(record)
    return record


@router.put("/{inspection_id}", response_model=InspectionResponse)
def update_inspection(inspection_id: int, body: InspectionCreate):
    """更新验车记录."""
    for r in _store:
        if r["id"] == inspection_id:
            r["photos"] = body.photos
            r["notes"] = body.notes
            r["mileage"] = body.mileage
            r["fuel_level"] = body.fuel_level
            r["updated_at"] = datetime.now().isoformat()
            return r
    raise HTTPException(status_code=404, detail="验车记录不存在")


@router.get("/{order_id}", response_model=InspectionResponse)
def get_inspection(order_id: int):
    """根据工单ID查询验车记录."""
    for r in _store:
        if r["order_id"] == order_id:
            return r
    raise HTTPException(status_code=404, detail="验车记录不存在")


@router.get("", response_model=list[InspectionResponse])
def list_inspections():
    """列出所有验车记录."""
    return list(_store)
