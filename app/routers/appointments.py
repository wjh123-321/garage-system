"""预约管理API - In-memory storage."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime


class AppointmentCreate(BaseModel):
    customer_name: str
    customer_phone: str
    car_plate: str
    car_model: str = ""
    appoint_date: str
    appoint_time: str
    description: str = ""


class AppointmentResponse(BaseModel):
    id: int
    customer_name: str
    customer_phone: str
    car_plate: str
    car_model: str
    appoint_date: str
    appoint_time: str
    description: str
    status: str
    created_at: str


router = APIRouter(prefix="/api/appointments", tags=["车主预约"])

# In-memory storage
_store = []
_counter = 0


@router.post("", response_model=AppointmentResponse, status_code=201)
def create_appointment(body: AppointmentCreate):
    global _counter
    _counter += 1
    now = datetime.now().isoformat()
    record = {
        "id": _counter,
        "customer_name": body.customer_name,
        "customer_phone": body.customer_phone,
        "car_plate": body.car_plate,
        "car_model": body.car_model,
        "appoint_date": body.appoint_date,
        "appoint_time": body.appoint_time,
        "description": body.description,
        "status": "pending",
        "created_at": now,
    }
    _store.append(record)
    return record


@router.get("", response_model=list[AppointmentResponse])
def get_appointments(phone: str = Query("", description="按手机号筛选")):
    if phone:
        return [a for a in _store if a["customer_phone"] == phone]
    return list(_store)


@router.get("/date/{date}", response_model=list[AppointmentResponse])
def get_appointments_by_date(date: str):
    results = [a for a in _store if a["appoint_date"] == date]
    return results


@router.put("/{appointment_id}/status", response_model=AppointmentResponse)
def update_appointment_status(appointment_id: int, new_status: str = Query(..., description="新状态")):
    for a in _store:
        if a["id"] == appointment_id:
            a["status"] = new_status
            return a
    raise HTTPException(status_code=404, detail="预约不存在")
