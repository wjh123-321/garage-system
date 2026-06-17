"""Part and inventory schemas."""

import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


class PartBase(BaseModel):
    name: str = Field(..., max_length=128, description="配件名称")
    sku: str = Field(..., max_length=64, description="SKU编码")
    category: str = Field(default="其他", max_length=32, description="分类")
    unit: str = Field(default="个", max_length=16, description="单位")
    quantity: int = Field(default=0, ge=0, description="当前库存")
    min_stock: int = Field(default=5, ge=0, description="最低库存预警")
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    supplier: str = Field(default="", max_length=128)
    remark: str = Field(default="", max_length=512)


class PartCreate(PartBase):
    pass


class PartUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    category: str | None = Field(default=None, max_length=32)
    unit: str | None = Field(default=None, max_length=16)
    unit_price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    min_stock: int | None = Field(default=None, ge=0)
    supplier: str | None = Field(default=None, max_length=128)
    remark: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None


class PartResponse(PartBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


class PartListResponse(BaseModel):
    items: list[PartResponse]
    total: int
    page: int
    page_size: int


class InventoryTransactionCreate(BaseModel):
    part_id: int
    type: str = Field(..., pattern=r"^(in|out)$")
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    reference_type: str = Field(default="", max_length=32)
    reference_id: int | None = None
    operator: str = Field(default="", max_length=64)
    remark: str = Field(default="", max_length=512)


class InventoryTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    part_name: str = ""
    type: str
    quantity: int
    unit_price: Decimal
    reference_type: str
    reference_id: int | None
    operator: str
    remark: str
    created_at: datetime.datetime


class InventoryTransactionListResponse(BaseModel):
    items: list[InventoryTransactionResponse]
    total: int
    page: int
    page_size: int
