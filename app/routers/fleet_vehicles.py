from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

router = APIRouter(prefix="/api/fleet", tags=["fleet-vehicles"])

# ---------------------------------------------------------------------------
# In-memory storage
# ---------------------------------------------------------------------------
_vehicles: list[dict] = []
_next_id: int = 1

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class VehicleCreate(BaseModel):
    plate: str
    brand: str
    model: str
    year: int
    vin: str
    driver: str
    insurance_date: str  # ISO date string, e.g. "2026-12-31"
    inspection_date: str
    status: str = Field(default="运行", pattern=r"^(运行|维修|停运)$")
    remark: str = ""


class VehicleUpdate(BaseModel):
    plate: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    vin: Optional[str] = None
    driver: Optional[str] = None
    insurance_date: Optional[str] = None
    inspection_date: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern=r"^(运行|维修|停运)$")
    remark: Optional[str] = None


class VehicleResponse(BaseModel):
    id: int
    plate: str
    brand: str
    model: str
    year: int
    vin: str
    driver: str
    insurance_date: str
    inspection_date: str
    status: str
    remark: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _now() -> str:
    return datetime.now().isoformat()


def _find(idx: int) -> dict:
    for v in _vehicles:
        if v["id"] == idx:
            return v
    raise HTTPException(status_code=404, detail="Vehicle not found")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("/vehicles", response_model=list[VehicleResponse])
def list_vehicles(keyword: Optional[str] = Query(None, min_length=1)):
    """Return all vehicles, optionally filtered by keyword on plate or driver."""
    if keyword:
        kw = keyword.lower()
        return [
            VehicleResponse(**v)
            for v in _vehicles
            if kw in v["plate"].lower() or kw in v["driver"].lower()
        ]
    return [VehicleResponse(**v) for v in _vehicles]


@router.post("/vehicles", response_model=VehicleResponse, status_code=201)
def create_vehicle(body: VehicleCreate):
    global _next_id
    now = _now()
    record = {
        "id": _next_id,
        "plate": body.plate,
        "brand": body.brand,
        "model": body.model,
        "year": body.year,
        "vin": body.vin,
        "driver": body.driver,
        "insurance_date": body.insurance_date,
        "inspection_date": body.inspection_date,
        "status": body.status,
        "remark": body.remark,
        "created_at": now,
        "updated_at": now,
    }
    _vehicles.append(record)
    _next_id += 1
    return VehicleResponse(**record)


@router.get("/vehicles/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: int):
    return VehicleResponse(**_find(vehicle_id))


@router.put("/vehicles/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(vehicle_id: int, body: VehicleUpdate):
    record = _find(vehicle_id)
    update_data = body.model_dump(exclude_unset=True)
    record.update(update_data)
    record["updated_at"] = _now()
    return VehicleResponse(**record)


@router.delete("/vehicles/{vehicle_id}", status_code=204)
def delete_vehicle(vehicle_id: int):
    record = _find(vehicle_id)
    _vehicles.remove(record)
    return None
