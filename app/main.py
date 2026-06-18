"""Garage Management System - FastAPI Application Entry Point."""

import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func

from .config import settings
from .database import engine, Base, get_db
from .routers import customers, work_orders, parts, reminders, ai as ai_router, vin, appointments, notifications, vision, reports, printing, finance, suppliers, performance, membership, reviews, templates, staff, inspection, quotations, parts_store, fleet_vehicles, fleet_fuel, fleet_finance, fleet_dashboard
from .models.customer import Customer
from .models.work_order import WorkOrder
from .models.part import Part
from .models.reminder import ServiceReminder
from .utils.cache import get_cache, set_cache

# 性能日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("perf")

# 前端构建产物路径
# Docker: /app/app/main.py → /app/frontend/dist/
# 本地开发: backend/app/main.py → frontend/dist/
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(_BASE, "frontend", "dist")


@asynccontextmanager
# trigger redeploy
async def lifespan(app: FastAPI):
    """Create tables on startup (dev convenience; use Alembic in production)."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS for React dev server + external access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ⚡ 性能监控中间件
@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    if elapsed > 0.5:  # 超过500ms记录慢查询
        logger.warning(f"SLOW: {request.method} {request.url.path} ({elapsed:.3f}s)")
    response.headers["X-Response-Time"] = f"{elapsed:.3f}s"
    return response


# Register routers
app.include_router(customers.router)
app.include_router(work_orders.router)
app.include_router(parts.router)
app.include_router(reminders.router)
app.include_router(ai_router.router)
app.include_router(vin.router)
app.include_router(appointments.router)
app.include_router(notifications.router)
app.include_router(vision.router)
app.include_router(suppliers.router)
app.include_router(printing.router)
app.include_router(reports.router)
app.include_router(finance.router)
app.include_router(performance.router)
app.include_router(membership.router)
app.include_router(reviews.router)
app.include_router(staff.router)
app.include_router(templates.router)
app.include_router(inspection.router)
app.include_router(quotations.router)
app.include_router(parts_store.router)
app.include_router(fleet_vehicles.router)
app.include_router(fleet_fuel.router)
app.include_router(fleet_finance.router)
app.include_router(fleet_dashboard.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    """Dashboard summary statistics (cached 15s)."""
    cached = get_cache("dashboard_stats")
    if cached:
        return cached

    customer_count = db.query(func.count(Customer.id)).filter(
        Customer.is_active == True
    ).scalar() or 0

    active_orders = db.query(func.count(WorkOrder.id)).filter(
        WorkOrder.status.in_(["pending", "diagnosing", "in_progress", "waiting_parts"])
    ).scalar() or 0

    today_orders = db.query(func.count(WorkOrder.id)).filter(
        func.date(WorkOrder.created_at) == func.current_date()
    ).scalar() or 0

    low_stock = db.query(func.count(Part.id)).filter(
        Part.is_active == True,
        Part.quantity <= Part.min_stock,
    ).scalar() or 0

    from datetime import datetime, timedelta, timezone
    week_later = datetime.now(timezone.utc) + timedelta(days=7)
    due_reminders = db.query(func.count(ServiceReminder.id)).filter(
        ServiceReminder.is_active == True,
        ServiceReminder.is_notified == False,
        ServiceReminder.next_service_date.isnot(None),
        ServiceReminder.next_service_date <= week_later,
    ).scalar() or 0

    result = {
        "customer_count": customer_count,
        "active_orders": active_orders,
        "today_orders": today_orders,
        "low_stock_parts": low_stock,
        "due_reminders": due_reminders,
    }
    set_cache("dashboard_stats", result, ttl_seconds=15)
    return result


# ── 前端静态文件托管 ──────────────────────────────────────
if os.path.isdir(FRONTEND_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    @app.get("/favicon.ico")
    async def favicon():
        return JSONResponse({}, status_code=204)

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend pages for client-side routing.

        API routes are handled by routers registered above;
        this catch-all only serves frontend static files.
        """
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        file_path = os.path.join(FRONTEND_DIR, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    logger.warning(f"前端构建目录不存在: {FRONTEND_DIR}，请先执行 cd frontend && npm run build")
