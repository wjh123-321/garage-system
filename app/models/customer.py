"""Customer model."""

import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="客户姓名")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True, comment="手机号")
    car_plate: Mapped[str] = mapped_column(String(16), nullable=False, index=True, comment="车牌号")
    car_model: Mapped[str] = mapped_column(String(64), default="", comment="车型")
    vin: Mapped[str] = mapped_column(String(32), default="", comment="车架号/VIN")
    mileage: Mapped[int] = mapped_column(default=0, comment="当前里程(km)")
    address: Mapped[str] = mapped_column(String(256), default="", comment="地址")
    remark: Mapped[str] = mapped_column(String(512), default="", comment="备注")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否活跃")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    work_orders = relationship("WorkOrder", back_populates="customer")
    reminders = relationship("ServiceReminder", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer {self.name} {self.car_plate}>"
