"""Parts and inventory API router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from ..database import get_db
from ..models.part import Part, InventoryTransaction
from ..schemas.part import (
    PartCreate,
    PartUpdate,
    PartResponse,
    PartListResponse,
    InventoryTransactionCreate,
    InventoryTransactionResponse,
    InventoryTransactionListResponse,
)

router = APIRouter(prefix="/api/parts", tags=["配件进销存"])


def _part_to_response(p: Part) -> PartResponse:
    return PartResponse(
        id=p.id,
        name=p.name,
        sku=p.sku,
        category=p.category,
        unit=p.unit,
        quantity=p.quantity,
        min_stock=p.min_stock,
        unit_price=p.unit_price,
        supplier=p.supplier,
        remark=p.remark,
        is_active=p.is_active,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("", response_model=PartListResponse)
def list_parts(
    keyword: str = Query("", max_length=64, description="搜索(名称/SKU/供应商)"),
    category: str = Query("", description="按分类筛选"),
    low_stock: bool = Query(False, description="仅显示低库存"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询配件列表，支持搜索和低库存预警"""
    q = db.query(Part).filter(Part.is_active == True)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            Part.name.ilike(like)
            | Part.sku.ilike(like)
            | Part.supplier.ilike(like)
        )
    if category:
        q = q.filter(Part.category == category)
    if low_stock:
        q = q.filter(Part.quantity <= Part.min_stock)

    total = q.count()
    parts = (
        q.order_by(Part.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [_part_to_response(p) for p in parts]
    return PartListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/categories", response_model=list[str])
def list_categories(db: Session = Depends(get_db)):
    """获取所有配件分类"""
    rows = db.query(Part.category).filter(Part.is_active == True).distinct().all()
    return sorted(set(row[0] for row in rows if row[0]))


@router.get("/low-stock", response_model=list[PartResponse])
def low_stock_parts(db: Session = Depends(get_db)):
    """获取所有库存不足的配件"""
    parts = (
        db.query(Part)
        .filter(Part.is_active == True, Part.quantity <= Part.min_stock)
        .all()
    )
    return [_part_to_response(p) for p in parts]


@router.get("/{part_id}", response_model=PartResponse)
def get_part(part_id: int, db: Session = Depends(get_db)):
    """查询配件详情"""
    p = db.query(Part).filter(Part.id == part_id).first()
    if not p:
        raise HTTPException(404, "配件不存在")
    return _part_to_response(p)


@router.post("", response_model=PartResponse, status_code=201)
def create_part(data: PartCreate, db: Session = Depends(get_db)):
    """创建配件"""
    existing = db.query(Part).filter(Part.sku == data.sku).first()
    if existing:
        raise HTTPException(400, f"SKU '{data.sku}' 已存在")
    p = Part(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _part_to_response(p)


@router.put("/{part_id}", response_model=PartResponse)
def update_part(part_id: int, data: PartUpdate, db: Session = Depends(get_db)):
    """更新配件信息"""
    p = db.query(Part).filter(Part.id == part_id).first()
    if not p:
        raise HTTPException(404, "配件不存在")
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return _part_to_response(p)


@router.delete("/{part_id}", status_code=204)
def delete_part(part_id: int, db: Session = Depends(get_db)):
    """删除配件（软删除）"""
    p = db.query(Part).filter(Part.id == part_id).first()
    if not p:
        raise HTTPException(404, "配件不存在")
    p.is_active = False
    db.commit()


# ---- Inventory Transactions ----

@router.get("/{part_id}/transactions", response_model=InventoryTransactionListResponse)
def list_part_transactions(
    part_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询某个配件的库存变动记录"""
    p = db.query(Part).filter(Part.id == part_id).first()
    if not p:
        raise HTTPException(404, "配件不存在")

    q = db.query(InventoryTransaction).filter(
        InventoryTransaction.part_id == part_id
    )
    total = q.count()
    txns = (
        q.order_by(InventoryTransaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        InventoryTransactionResponse(
            id=t.id,
            part_id=t.part_id,
            part_name=p.name,
            type=t.type,
            quantity=t.quantity,
            unit_price=t.unit_price,
            reference_type=t.reference_type,
            reference_id=t.reference_id,
            operator=t.operator,
            remark=t.remark,
            created_at=t.created_at,
        )
        for t in txns
    ]
    return InventoryTransactionListResponse(
        items=items, total=total, page=page, page_size=page_size
    )


@router.post("/transactions", response_model=InventoryTransactionResponse, status_code=201)
def create_inventory_transaction(
    data: InventoryTransactionCreate, db: Session = Depends(get_db)
):
    """入库/出库操作（自动更新库存数量）"""
    part = db.query(Part).filter(Part.id == data.part_id).first()
    if not part:
        raise HTTPException(404, "配件不存在")

    if data.type == "out" and part.quantity < data.quantity:
        raise HTTPException(400, f"库存不足: 当前 {part.quantity}, 需要 {data.quantity}")

    # 更新库存
    if data.type == "in":
        part.quantity += data.quantity
    else:
        part.quantity -= data.quantity

    txn = InventoryTransaction(**data.model_dump())
    db.add(txn)
    db.commit()
    db.refresh(txn)

    return InventoryTransactionResponse(
        id=txn.id,
        part_id=txn.part_id,
        part_name=part.name,
        type=txn.type,
        quantity=txn.quantity,
        unit_price=txn.unit_price,
        reference_type=txn.reference_type,
        reference_id=txn.reference_id,
        operator=txn.operator,
        remark=txn.remark,
        created_at=txn.created_at,
    )
