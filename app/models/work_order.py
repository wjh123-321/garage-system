"""Work order and work order item models."""

import datetime
from sqlalchemy import (
    String, Integer, Float, DateTime, Text, ForeignKey, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_no: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True, comment="工单编号"
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), nullable=False, comment="客户ID"
    )
    car_plate: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="车牌号")
    car_model: Mapped[str] = mapped_column(String(64), default="", comment="车型")
    vin: Mapped[str] = mapped_column(String(32), default="", comment="车架号")
    mileage: Mapped[int] = mapped_column(default=0, comment="进厂里程")
    status: Mapped[str] = mapped_column(
        String(20), default="pending", index=True,
        comment="状态: pending/ diagnosing / in_progress / waiting_parts / completed / cancelled"
    )
    description: Mapped[str] = mapped_column(Text, default="", comment="故障描述")
    technician: Mapped[str] = mapped_column(String(64), default="", comment="维修技师")
    total_amount: Mapped[float] = mapped_column(
        Float, default=0.0, comment="总金额"
    )
    remark: Mapped[str] = mapped_column(Text, default="", comment="备注")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完工时间"
    )

    customer = relationship("Customer", back_populates="work_orders")
    items = relationship(
        "WorkOrderItem", back_populates="work_order",
        cascade="all, delete-orphan",
        order_by="WorkOrderItem.id",
    )

    def __repr__(self) -> str:
        return f"<WorkOrder {self.order_no} [{self.status}]>"


class WorkOrderItem(Base):
    __tablename__ = "work_order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False
    )
    item_type: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="类型: part(配件) / labor(工时)"
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="项目名称")
    part_id: Mapped[int | None] = mapped_column(
        ForeignKey("parts.id"), nullable=True, comment="关联配件ID"
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, comment="数量")
    unit_price: Mapped[float] = mapped_column(
        Float, default=0.0, comment="单价"
    )
    total_price: Mapped[float] = mapped_column(
        Float, default=0.0, comment="小计"
    )

    work_order = relationship("WorkOrder", back_populates="items")
