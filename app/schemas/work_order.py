"""Work order schemas."""

import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class WorkOrderItemBase(BaseModel):
    item_type: str = Field(..., pattern=r"^(part|labor)$", description="part(配件) / labor(工时)")
    name: str = Field(..., max_length=128)
    part_id: int | None = None
    quantity: int = Field(default=1, ge=1)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    total_price: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)


class WorkOrderItemCreate(WorkOrderItemBase):
    pass


class WorkOrderItemResponse(WorkOrderItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    work_order_id: int


class WorkOrderBase(BaseModel):
    customer_id: int = Field(..., description="客户ID")
    car_plate: str = Field(..., max_length=16)
    car_model: str = Field(default="", max_length=64)
    vin: str = Field(default="", max_length=32)
    mileage: int = Field(default=0, ge=0)
    description: str = Field(default="", description="故障描述")
    technician: str = Field(default="", max_length=64, description="维修技师")
    remark: str = Field(default="", max_length=512)


class WorkOrderCreate(WorkOrderBase):
    items: list[WorkOrderItemCreate] = []


class WorkOrderUpdate(BaseModel):
    status: str | None = Field(
        default=None,
        pattern=r"^(pending|diagnosing|in_progress|waiting_parts|completed|cancelled)$",
    )
    description: str | None = None
    technician: str | None = None
    mileage: int | None = Field(default=None, ge=0)
    remark: str | None = None
    items: list[WorkOrderItemCreate] | None = None


class WorkOrderListResponse(BaseModel):
    items: list["WorkOrderResponse"]
    total: int
    page: int
    page_size: int


class WorkOrderResponse(WorkOrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    status: str
    total_amount: Decimal
    completed_at: datetime.datetime | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    items: list[WorkOrderItemResponse] = []
    customer_name: str = ""
    customer_phone: str = ""
