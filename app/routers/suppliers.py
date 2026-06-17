"""Supplier API router — in-memory store with optional JSON file persistence.

Suppliers are not backed by the database; data is kept in a process-level dict
and optionally persisted to a JSON file (set SUPPLIERS_DATA_FILE env var).
"""

import os
import json
import datetime
import threading
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/suppliers", tags=["供应商管理"])

# ── In-memory store ──────────────────────────────────────
_lock = threading.Lock()
_store: dict[int, dict] = {}
_next_id: int = 1

DATA_FILE = os.environ.get(
    "SUPPLIERS_DATA_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "suppliers.json"),
)


def _load():
    """Load store from JSON file on first access."""
    global _next_id, _store
    if _store or not os.path.isfile(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            entries = json.load(f)
        if isinstance(entries, list):
            for e in entries:
                _store[e["id"]] = e
            _next_id = (max(e["id"] for e in entries) + 1) if entries else 1
    except (json.JSONDecodeError, OSError):
        _store = {}


def _save():
    """Flush store to JSON file."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(list(_store.values()), f, ensure_ascii=False, indent=2, default=str)


# ── Schemas ──────────────────────────────────────────────

class SupplierBase(BaseModel):
    name: str = Field(..., max_length=128, description="供应商/厂商名称")
    contact: str = Field(default="", max_length=32, description="联系人")
    phone: str = Field(default="", max_length=20, description="联系电话")
    address: str = Field(default="", max_length=256, description="地址")
    remark: str = Field(default="", max_length=512, description="备注")
    is_active: bool = True


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    contact: Optional[str] = Field(default=None, max_length=32)
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=256)
    remark: Optional[str] = Field(default=None, max_length=512)
    is_active: Optional[bool] = None


class SupplierResponse(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class SupplierListResponse(BaseModel):
    items: list[SupplierResponse]
    total: int
    page: int
    page_size: int


# ── Helpers ──────────────────────────────────────────────

def _to_response(record: dict) -> SupplierResponse:
    return SupplierResponse(**record)


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


# ── Routes ───────────────────────────────────────────────

@router.get("", response_model=SupplierListResponse)
def list_suppliers(
    keyword: str = Query("", max_length=64, description="搜索关键词(名称/联系人/电话)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询供应商列表，支持模糊搜索"""
    with _lock:
        _load()
        entries = list(_store.values())

    if keyword:
        lower = keyword.lower()
        entries = [
            e for e in entries
            if lower in e["name"].lower()
            or lower in e["contact"].lower()
            or lower in e["phone"].lower()
        ]

    total = len(entries)
    entries.sort(key=lambda e: e["id"], reverse=True)
    page_entries = entries[(page - 1) * page_size : page * page_size]
    items = [_to_response(e) for e in page_entries]
    return SupplierListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: int):
    """查询单个供应商详情"""
    with _lock:
        _load()
        record = _store.get(supplier_id)
    if not record:
        raise HTTPException(404, "供应商不存在")
    return _to_response(record)


@router.post("", response_model=SupplierResponse, status_code=201)
def create_supplier(data: SupplierCreate):
    """创建供应商"""
    now = _now()
    record = data.model_dump()
    record["id"] = None  # placeholder, set below
    record["created_at"] = now.isoformat()
    record["updated_at"] = now.isoformat()

    with _lock:
        _load()
        global _next_id
        record["id"] = _next_id
        _next_id += 1
        _store[record["id"]] = record
        _save()

    return _to_response(record)


@router.put("/{supplier_id}", response_model=SupplierResponse)
def update_supplier(supplier_id: int, data: SupplierUpdate):
    """更新供应商信息"""
    with _lock:
        _load()
        record = _store.get(supplier_id)
        if not record:
            raise HTTPException(404, "供应商不存在")

        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            if v is not None:
                record[k] = v
        record["updated_at"] = _now().isoformat()
        _save()

    return _to_response(record)


@router.delete("/{supplier_id}", status_code=204)
def delete_supplier(supplier_id: int):
    """删除供应商（软删除：is_active=False）"""
    with _lock:
        _load()
        record = _store.get(supplier_id)
        if not record:
            raise HTTPException(404, "供应商不存在")
        record["is_active"] = False
        record["updated_at"] = _now().isoformat()
        _save()
