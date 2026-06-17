"""Staff API router - in-memory employee management."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

router = APIRouter(prefix="/api/staff", tags=["员工管理"])


# ── Data models ──────────────────────────────────────────────

class StaffRole(str, Enum):
    boss = "boss"
    tech = "tech"
    sa = "sa"  # Service Advisor


class StaffCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=32, description="姓名")
    role: StaffRole = Field(..., description="角色: boss/tech/sa")


class StaffUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=32)
    role: Optional[StaffRole] = None


class StaffResponse(BaseModel):
    id: int
    name: str
    role: StaffRole

    model_config = {"from_attributes": True}


class StaffListResponse(BaseModel):
    items: list[StaffResponse]
    total: int


# ── In-memory store ─────────────────────────────────────────

_staff_db: list[dict] = []
_next_id: int = 1

# Seed data
_seed = [
    {"name": "张师傅", "role": StaffRole.tech},
    {"name": "李师傅", "role": StaffRole.tech},
    {"name": "王店长", "role": StaffRole.boss},
    {"name": "赵顾问", "role": StaffRole.sa},
]
for s in _seed:
    _staff_db.append({"id": _next_id, **s})
    _next_id += 1

_ROLE_LABEL = {
    StaffRole.boss: "老板",
    StaffRole.tech: "技师",
    StaffRole.sa: "服务顾问",
}


def _to_response(staff: dict) -> StaffResponse:
    return StaffResponse(id=staff["id"], name=staff["name"], role=staff["role"])


# ── Endpoints ────────────────────────────────────────────────

@router.get("", response_model=StaffListResponse)
def list_staff(
    keyword: str = Query("", max_length=32, description="按姓名搜索"),
    role: Optional[StaffRole] = Query(None, description="按角色过滤"),
):
    """查询员工列表，支持姓名搜索和角色过滤。"""
    items = _staff_db[:]
    if keyword:
        items = [s for s in items if keyword in s["name"]]
    if role:
        items = [s for s in items if s["role"] == role]
    return StaffListResponse(
        items=[_to_response(s) for s in items],
        total=len(items),
    )


@router.get("/{staff_id}", response_model=StaffResponse)
def get_staff(staff_id: int):
    """查询单个员工详情。"""
    for s in _staff_db:
        if s["id"] == staff_id:
            return _to_response(s)
    raise HTTPException(404, "员工不存在")


@router.post("", response_model=StaffResponse, status_code=201)
def create_staff(data: StaffCreate):
    """添加员工。"""
    global _next_id
    staff = {"id": _next_id, "name": data.name, "role": data.role}
    _staff_db.append(staff)
    _next_id += 1
    return _to_response(staff)


@router.put("/{staff_id}", response_model=StaffResponse)
def update_staff(staff_id: int, data: StaffUpdate):
    """更新员工信息。"""
    for s in _staff_db:
        if s["id"] == staff_id:
            if data.name is not None:
                s["name"] = data.name
            if data.role is not None:
                s["role"] = data.role
            return _to_response(s)
    raise HTTPException(404, "员工不存在")


@router.delete("/{staff_id}", status_code=204)
def delete_staff(staff_id: int):
    """删除员工。"""
    for i, s in enumerate(_staff_db):
        if s["id"] == staff_id:
            _staff_db.pop(i)
            return
    raise HTTPException(404, "员工不存在")
