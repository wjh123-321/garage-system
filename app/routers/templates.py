"""Repair templates CRUD router (in-memory storage)."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

router = APIRouter(prefix="/api/templates", tags=["维修模板"])

# ── Schemas ──────────────────────────────────────────────


class TemplateItem(BaseModel):
    """Single repair item within a template."""
    name: str
    labor_hours: float = Field(ge=0, description="工时")
    price: float = Field(ge=0, description="价格(元)")


class TemplateCreate(BaseModel):
    """Payload for creating a new template."""
    name: str = Field(min_length=1, max_length=100)
    items: list[TemplateItem] = []
    category: str = ""


class TemplateUpdate(BaseModel):
    """Payload for updating an existing template."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    items: Optional[list[TemplateItem]] = None
    category: Optional[str] = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    items: list[TemplateItem]
    category: str
    total_price: float = 0
    total_hours: float = 0


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
    total: int
    page: int
    page_size: int


# ── In-memory storage ────────────────────────────────────

_templates: list[dict] = []
_next_id: int = 1


def _to_response(t: dict) -> TemplateResponse:
    items = [TemplateItem(**i) for i in t["items"]]
    total_price = round(sum(i.price for i in items), 2)
    total_hours = round(sum(i.labor_hours for i in items), 2)
    return TemplateResponse(
        id=t["id"],
        name=t["name"],
        items=items,
        category=t["category"],
        total_price=total_price,
        total_hours=total_hours,
    )


# ── CRUD Endpoints ───────────────────────────────────────


@router.get("", response_model=TemplateListResponse)
def list_templates(
    keyword: str = Query("", max_length=64, description="搜索模板名称"),
    category: str = Query("", description="按分类筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """查询维修模板列表"""
    q = _templates[:]
    if keyword:
        q = [t for t in q if keyword.lower() in t["name"].lower()]
    if category:
        q = [t for t in q if t["category"] == category]

    total = len(q)
    start = (page - 1) * page_size
    items = [_to_response(t) for t in q[start: start + page_size]]
    return TemplateListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/categories", response_model=list[str])
def list_categories():
    """获取所有模板分类"""
    cats = sorted(set(t["category"] for t in _templates if t["category"]))
    return cats


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(template_id: int):
    """查询维修模板详情"""
    for t in _templates:
        if t["id"] == template_id:
            return _to_response(t)
    raise HTTPException(404, "模板不存在")


@router.post("", response_model=TemplateResponse, status_code=201)
def create_template(data: TemplateCreate):
    """创建维修模板"""
    global _next_id
    t = {
        "id": _next_id,
        "name": data.name,
        "items": [i.model_dump() for i in data.items],
        "category": data.category,
    }
    _next_id += 1
    _templates.append(t)
    return _to_response(t)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(template_id: int, data: TemplateUpdate):
    """更新维修模板"""
    for t in _templates:
        if t["id"] == template_id:
            if data.name is not None:
                t["name"] = data.name
            if data.items is not None:
                t["items"] = [i.model_dump() for i in data.items]
            if data.category is not None:
                t["category"] = data.category
            return _to_response(t)
    raise HTTPException(404, "模板不存在")


@router.delete("/{template_id}", status_code=204)
def delete_template(template_id: int):
    """删除维修模板"""
    for i, t in enumerate(_templates):
        if t["id"] == template_id:
            _templates.pop(i)
            return
    raise HTTPException(404, "模板不存在")
