"""Reminder schemas."""

import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReminderBase(BaseModel):
    customer_id: int
    car_plate: str = Field(..., max_length=16)
    reminder_type: str = Field(
        ..., pattern=r"^(maintenance|inspection|insurance|other)$"
    )
    title: str = Field(..., max_length=128)
    description: str = Field(default="", max_length=512)
    last_service_date: datetime.datetime | None = None
    next_service_date: datetime.datetime | None = None
    mileage_remind: int = Field(default=0, ge=0)


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    last_service_date: datetime.datetime | None = None
    next_service_date: datetime.datetime | None = None
    mileage_remind: int | None = Field(default=None, ge=0)
    is_notified: bool | None = None
    is_active: bool | None = None


class ReminderResponse(ReminderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_notified: bool
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    customer_name: str = ""
    customer_phone: str = ""


class ReminderListResponse(BaseModel):
    items: list[ReminderResponse]
    total: int
    page: int
    page_size: int
