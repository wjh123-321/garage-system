"""Customer schemas."""

import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    name: str = Field(..., max_length=64, description="客户姓名")
    phone: str = Field(..., max_length=20, description="手机号")
    car_plate: str = Field(..., max_length=16, description="车牌号")
    car_model: str = Field(default="", max_length=64, description="车型")
    vin: str = Field(default="", max_length=32, description="车架号/VIN")
    mileage: int = Field(default=0, ge=0, description="当前里程(km)")
    address: str = Field(default="", max_length=256, description="地址")
    remark: str = Field(default="", max_length=512, description="备注")


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=20)
    car_plate: str | None = Field(default=None, max_length=16)
    car_model: str | None = Field(default=None, max_length=64)
    vin: str | None = Field(default=None, max_length=32)
    mileage: int | None = Field(default=None, ge=0)
    address: str | None = Field(default=None, max_length=256)
    remark: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    work_order_count: int = 0


class CustomerListResponse(BaseModel):
    items: list[CustomerResponse]
    total: int
    page: int
    page_size: int
