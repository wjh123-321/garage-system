"""Part inventory and transaction models."""

import datetime
from sqlalchemy import (
    String, Integer, Float, DateTime, Text, ForeignKey, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Part(Base):
    """配件主表"""
    __tablename__ = "parts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="配件名称")
    sku: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True, comment="SKU编码"
    )
    category: Mapped[str] = mapped_column(
        String(32), default="其他", index=True, comment="分类"
    )
    unit: Mapped[str] = mapped_column(String(16), default="个", comment="单位")
    quantity: Mapped[int] = mapped_column(Integer, default=0, comment="当前库存")
    min_stock: Mapped[int] = mapped_column(Integer, default=5, comment="最低库存预警")
    unit_price: Mapped[float] = mapped_column(
        Float, default=0.0, comment="单价(元)"
    )
    supplier: Mapped[str] = mapped_column(String(128), default="", comment="供应商")
    remark: Mapped[str] = mapped_column(Text, default="", comment="备注")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    transactions = relationship(
        "InventoryTransaction", back_populates="part",
        cascade="all, delete-orphan",
        order_by="InventoryTransaction.created_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<Part {self.name} ({self.sku}) qty={self.quantity}>"


class InventoryTransaction(Base):
    """库存变动记录"""
    __tablename__ = "inventory_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    part_id: Mapped[int] = mapped_column(
        ForeignKey("parts.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(8), nullable=False, comment="类型: in(入库) / out(出库)"
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, comment="数量")
    unit_price: Mapped[float] = mapped_column(
        Float, default=0.0, comment="变动时单价"
    )
    reference_type: Mapped[str] = mapped_column(
        String(32), default="", comment="关联类型: purchase_order / work_order / adjustment"
    )
    reference_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="关联单据ID"
    )
    operator: Mapped[str] = mapped_column(String(64), default="", comment="操作人")
    remark: Mapped[str] = mapped_column(Text, default="", comment="备注")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="操作时间"
    )

    part = relationship("Part", back_populates="transactions")
