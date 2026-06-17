"""Customer API router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models.customer import Customer
from ..models.work_order import WorkOrder
from ..schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
)

router = APIRouter(prefix="/api/customers", tags=["客户管理"])


def _to_response(c: Customer, wo_count: int = 0) -> CustomerResponse:
    return CustomerResponse(
        id=c.id,
        name=c.name,
        phone=c.phone,
        car_plate=c.car_plate,
        car_model=c.car_model,
        vin=c.vin,
        mileage=c.mileage,
        address=c.address,
        remark=c.remark,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at,
        work_order_count=wo_count,
    )


@router.get("", response_model=CustomerListResponse)
def list_customers(
    keyword: str = Query("", max_length=64, description="搜索关键词(姓名/手机/车牌)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """查询客户列表，支持按姓名/手机/车牌模糊搜索"""
    q = db.query(Customer)
    if keyword:
        like = f"%{keyword}%"
        q = q.filter(
            Customer.name.ilike(like)
            | Customer.phone.ilike(like)
            | Customer.car_plate.ilike(like)
        )
    total = q.count()
    customers = q.order_by(Customer.id.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # batch fetch work order counts
    customer_ids = [c.id for c in customers]
    counts = (
        db.query(WorkOrder.customer_id, func.count(WorkOrder.id))
        .filter(WorkOrder.customer_id.in_(customer_ids))
        .group_by(WorkOrder.customer_id)
        .all()
    )
    count_map = {row[0]: row[1] for row in counts}

    items = [_to_response(c, count_map.get(c.id, 0)) for c in customers]
    return CustomerListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """查询单个客户详情"""
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "客户不存在")
    wo_count = db.query(func.count(WorkOrder.id)).filter(
        WorkOrder.customer_id == customer_id
    ).scalar() or 0
    return _to_response(c, wo_count)


@router.post("", response_model=CustomerResponse, status_code=201)
def create_customer(data: CustomerCreate, db: Session = Depends(get_db)):
    """创建客户"""
    c = Customer(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_response(c)


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int, data: CustomerUpdate, db: Session = Depends(get_db)
):
    """更新客户信息"""
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "客户不存在")
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    wo_count = db.query(func.count(WorkOrder.id)).filter(
        WorkOrder.customer_id == customer_id
    ).scalar() or 0
    return _to_response(c, wo_count)


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    """删除客户（软删除：is_active=False）"""
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "客户不存在")
    c.is_active = False
    db.commit()
