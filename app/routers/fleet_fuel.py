"""
油耗记录API - 内存模拟
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

router = APIRouter(prefix="/api/fleet/fuel", tags=["Fleet Fuel"])

# ---------- 内存存储 ----------

_fuel_records: list[dict] = []
_next_id = 1

# ---------- 请求/响应模型 ----------


class FuelRecordCreate(BaseModel):
    vehicle_id: int
    date: date
    mileage: float = Field(..., ge=0, description="里程(km)")
    liters: float = Field(..., gt=0, description="加油升数(L)")
    amount: float = Field(..., gt=0, description="金额(元)")
    station: str = Field(default="", max_length=100, description="加油站")
    remark: str = Field(default="", max_length=200)


class FuelRecordOut(BaseModel):
    id: int
    vehicle_id: int
    date: date
    mileage: float
    liters: float
    amount: float
    station: str
    remark: str


# ---------- 端点 ----------


@router.get("", response_model=list[FuelRecordOut])
def list_fuel_records(
    vehicle_id: Optional[int] = Query(None, description="按车辆筛选"),
    start: Optional[date] = Query(None, description="起始日期"),
    end: Optional[date] = Query(None, description="截止日期"),
):
    """油耗记录列表，支持按车辆和日期范围筛选。"""
    result = _fuel_records[:]

    if vehicle_id is not None:
        result = [r for r in result if r["vehicle_id"] == vehicle_id]

    if start is not None:
        result = [r for r in result if r["date"] >= start]

    if end is not None:
        result = [r for r in result if r["date"] <= end]

    result.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    return result


@router.post("", response_model=FuelRecordOut, status_code=201)
def create_fuel_record(body: FuelRecordCreate):
    """创建油耗记录。"""
    global _next_id
    record = {
        "id": _next_id,
        "vehicle_id": body.vehicle_id,
        "date": body.date,
        "mileage": body.mileage,
        "liters": body.liters,
        "amount": body.amount,
        "station": body.station,
        "remark": body.remark,
    }
    _next_id += 1
    _fuel_records.append(record)
    return record


@router.delete("/{record_id}", status_code=204)
def delete_fuel_record(record_id: int):
    """删除油耗记录。"""
    global _fuel_records
    before = len(_fuel_records)
    _fuel_records = [r for r in _fuel_records if r["id"] != record_id]
    if len(_fuel_records) == before:
        raise HTTPException(status_code=404, detail="记录不存在")
