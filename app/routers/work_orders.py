"""Work order API router."""

import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from ..database import get_db
from ..models.customer import Customer
from ..models.work_order import WorkOrder, WorkOrderItem
from ..schemas.work_order import (
    WorkOrderCreate,
    WorkOrderUpdate,
    WorkOrderResponse,
    WorkOrderListResponse,
    WorkOrderItemCreate,
)

router = APIRouter(prefix="/api/work-orders", tags=["工单管理"])

ORDER_NO_PREFIX = "WO"


def _generate_order_no(db: Session) -> str:
    """生成唯一工单编号: WO + yyyyMMdd + 4位序号"""
    today = datetime.date.today().strftime("%Y%m%d")
    prefix = f"{ORDER_NO_PREFIX}{today}"
    last = (
        db.query(func.max(WorkOrder.order_no))
        .filter(WorkOrder.order_no.like(f"{prefix}%"))
        .scalar()
    )
    if last:
        seq = int(last[-4:]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _calc_total(items_data: list[WorkOrderItemCreate]) -> Decimal:
    total = Decimal("0.00")
    for item in items_data:
        if item.total_price == Decimal("0.00") and item.unit_price > 0:
            item.total_price = item.unit_price * item.quantity
        total += item.total_price
    return total


def _to_response(wo: WorkOrder) -> WorkOrderResponse:
    customer = wo.customer
    return WorkOrderResponse(
        id=wo.id,
        order_no=wo.order_no,
        customer_id=wo.customer_id,
        car_plate=wo.car_plate,
        car_model=wo.car_model,
        vin=wo.vin,
        mileage=wo.mileage,
        status=wo.status,
        description=wo.description,
        technician=wo.technician,
        total_amount=wo.total_amount,
        remark=wo.remark,
        completed_at=wo.completed_at,
        created_at=wo.created_at,
        updated_at=wo.updated_at,
        items=[
            {
                "id": i.id,
                "work_order_id": i.work_order_id,
                "item_type": i.item_type,
                "name": i.name,
                "part_id": i.part_id,
                "quantity": i.quantity,
                "unit_price": i.unit_price,
                "total_price": i.total_price,
            }
            for i in wo.items
        ],
        customer_name=customer.name if customer else "",
        customer_phone=customer.phone if customer else "",
    )


@router.get("", response_model=WorkOrderListResponse)
def list_work_orders(
    keyword: str = Query("", max_length=64, description="搜索(工单号/车牌/客户)"),
    status: str = Query("", description="按状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """工单列表，支持搜索和状态筛选"""
    # 使用 contains_eager + 子查询避免 joinedload 的笛卡尔积
    from sqlalchemy.orm import contains_eager

    # 先查 ids 再查详情，分页在子查询做
    base = db.query(WorkOrder.id)

    if status:
        base = base.filter(WorkOrder.status == status)
    if keyword:
        like = f"%{keyword}%"
        base = base.filter(
            WorkOrder.order_no.ilike(like)
            | WorkOrder.car_plate.ilike(like)
            | WorkOrder.customer.has(Customer.name.ilike(like))
            | WorkOrder.customer.has(Customer.phone.ilike(like))
        )

    total = base.count()
    ids = base.order_by(WorkOrder.id.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).subquery()

    orders = (
        db.query(WorkOrder)
        .join(ids, WorkOrder.id == ids.c.id)
        .options(joinedload(WorkOrder.customer))
        .order_by(WorkOrder.id.desc())
        .all()
    )

    items = [_to_response(o) for o in orders]
    return WorkOrderListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{order_id}", response_model=WorkOrderResponse)
def get_work_order(order_id: int, db: Session = Depends(get_db)):
    """查询单个工单详情"""
    wo = (
        db.query(WorkOrder)
        .options(joinedload(WorkOrder.customer), joinedload(WorkOrder.items))
        .filter(WorkOrder.id == order_id)
        .first()
    )
    if not wo:
        raise HTTPException(404, "工单不存在")
    return _to_response(wo)


@router.get("/plate/{car_plate}", response_model=list[WorkOrderResponse])
def get_orders_by_plate(car_plate: str, db: Session = Depends(get_db)):
    """扫码查车 - 按车牌号查询所有工单"""
    orders = (
        db.query(WorkOrder)
        .options(joinedload(WorkOrder.customer), joinedload(WorkOrder.items))
        .filter(WorkOrder.car_plate == car_plate)
        .order_by(WorkOrder.id.desc())
        .all()
    )
    return [_to_response(o) for o in orders]


@router.post("", response_model=WorkOrderResponse, status_code=201)
def create_work_order(data: WorkOrderCreate, db: Session = Depends(get_db)):
    """创建工单"""
    customer = db.query(Customer).filter(Customer.id == data.customer_id).first()
    if not customer:
        raise HTTPException(400, "客户不存在")

    order_no = _generate_order_no(db)

    # auto-fill car info from customer if not provided
    car_plate = data.car_plate or customer.car_plate
    car_model = data.car_model or customer.car_model
    vin = data.vin or customer.vin

    total = _calc_total(data.items) if data.items else Decimal("0.00")

    wo = WorkOrder(
        order_no=order_no,
        customer_id=data.customer_id,
        car_plate=car_plate,
        car_model=car_model,
        vin=vin,
        mileage=data.mileage,
        description=data.description,
        technician=data.technician,
        total_amount=total,
        remark=data.remark,
    )
    db.add(wo)
    db.flush()  # get wo.id

    for item_data in data.items:
        item = WorkOrderItem(
            work_order_id=wo.id,
            **item_data.model_dump(),
        )
        db.add(item)

    db.commit()
    db.refresh(wo)
    # reload with relationships
    wo = (
        db.query(WorkOrder)
        .options(joinedload(WorkOrder.customer), joinedload(WorkOrder.items))
        .filter(WorkOrder.id == wo.id)
        .first()
    )
    return _to_response(wo)


@router.put("/{order_id}", response_model=WorkOrderResponse)
def update_work_order(
    order_id: int, data: WorkOrderUpdate, db: Session = Depends(get_db)
):
    """更新工单（状态流转、修改明细）"""
    wo = (
        db.query(WorkOrder)
        .options(joinedload(WorkOrder.customer), joinedload(WorkOrder.items))
        .filter(WorkOrder.id == order_id)
        .first()
    )
    if not wo:
        raise HTTPException(404, "工单不存在")

    update_data = data.model_dump(exclude_unset=True)
    items_data = update_data.pop("items", None)

    for k, v in update_data.items():
        setattr(wo, k, v)

    # if completed, set completed_at
    if data.status == "completed" and wo.completed_at is None:
        wo.completed_at = datetime.datetime.now(datetime.timezone.utc)

    # replace items if provided
    if items_data is not None:
        db.query(WorkOrderItem).filter(
            WorkOrderItem.work_order_id == order_id
        ).delete()
        for item_data in items_data:
            item = WorkOrderItem(work_order_id=order_id, **item_data)
            db.add(item)
        # Use the original Pydantic model objects (data.items) instead of
        # the serialized dicts (items_data) for _calc_total, which expects
        # attribute access via WorkOrderItemCreate.total_price
        total = _calc_total(data.items) if data.items else Decimal("0.00")
        wo.total_amount = total

    db.commit()
    db.refresh(wo)
    wo = (
        db.query(WorkOrder)
        .options(joinedload(WorkOrder.customer), joinedload(WorkOrder.items))
        .filter(WorkOrder.id == order_id)
        .first()
    )
    return _to_response(wo)


@router.delete("/{order_id}", status_code=204)
def delete_work_order(order_id: int, db: Session = Depends(get_db)):
    """删除工单"""
    wo = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not wo:
        raise HTTPException(404, "工单不存在")
    db.delete(wo)
    db.commit()
