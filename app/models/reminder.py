"""Service reminder model."""

import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class ServiceReminder(Base):
    """服务提醒表 - 保养/年检/保险到期提醒"""
    __tablename__ = "service_reminders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), nullable=False
    )
    car_plate: Mapped[str] = mapped_column(String(16), nullable=False, comment="车牌号")
    reminder_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="类型: maintenance / inspection / insurance / other"
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="提醒标题")
    description: Mapped[str] = mapped_column(Text, default="", comment="说明")
    last_service_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="上次服务日期"
    )
    next_service_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="下次到期日期"
    )
    mileage_remind: Mapped[int] = mapped_column(
        Integer, default=0, comment="提醒里程(km), 0表示不按里程提醒"
    )
    is_notified: Mapped[bool] = mapped_column(default=False, comment="是否已通知")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    customer = relationship("Customer", back_populates="reminders")

    def __repr__(self) -> str:
        return f"<ServiceReminder {self.title} [{self.car_plate}]>"
