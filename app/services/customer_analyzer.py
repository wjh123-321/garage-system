"""Customer analysis service.

Provides rule-based customer churn prediction, maintenance schedule
recommendations based on vehicle model + mileage, and visit prioritization
scoring for callback scheduling.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.customer import Customer
from ..models.work_order import WorkOrder
from ..models.reminder import ServiceReminder

logger = logging.getLogger("customer_analyzer")

# ── Maintenance interval rules ──────────────────────────────

MAINTENANCE_RULES: list[dict[str, Any]] = [
    {
        "service": "常规保养",
        "interval_km": 5000,
        "interval_months": 6,
        "description": "每5000km/6个月",
    },
    {
        "service": "机油",
        "interval_km": 10000,
        "interval_months": None,
        "description": "每5000-10000km",
    },
    {
        "service": "刹车片",
        "interval_km": 50000,
        "interval_months": None,
        "description": "每30000-50000km",
    },
    {
        "service": "轮胎",
        "interval_km": 80000,
        "interval_months": None,
        "description": "每50000-80000km",
    },
    {
        "service": "变速箱油",
        "interval_km": 60000,
        "interval_months": None,
        "description": "每60000km",
    },
    {
        "service": "防冻液",
        "interval_km": 40000,
        "interval_months": 24,
        "description": "每2年/40000km",
    },
    {
        "service": "空调滤芯",
        "interval_km": 10000,
        "interval_months": 12,
        "description": "每10000km/1年",
    },
]


def _ensure_aware(dt: datetime | None) -> datetime | None:
    """Convert a naive datetime to aware (UTC) for safe arithmetic."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class CustomerAnalyzer:
    """Rule-based customer churn, maintenance, and callback-priority analysis.

    Parameters
    ----------
    db : Session
        Active SQLAlchemy database session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── 1. 流失预警 ─────────────────────────────────────

    def get_at_risk_customers(self) -> dict[str, Any]:
        """Identify all active customers at risk of churn.

        Returns a dict keyed by risk level (``"high"`` / ``"medium"`` /
        ``"low"``) containing customer lists and a ``"counts"`` summary.

        Risk levels are based on days since last completed work order:

        * >90 days  → **high**   (score 0.7–1.0)
        * 60–90     → **medium** (score 0.4–0.7)
        * 30–60     → **low**    (score 0.1–0.4)
        * <30       → **none**   (not included in results)

        Score formula
        -------------
        ``(days_since / 365 * 0.5) + (1 - min(visits / 20, 1)) * 0.3
        + (1 - min(avg_spend / 10000, 1)) * 0.2``
        """
        now = datetime.now(timezone.utc)
        customers = (
            self.db.query(Customer)
            .filter(Customer.is_active == True)
            .all()
        )

        result: dict[str, Any] = {
            "high": [],
            "medium": [],
            "low": [],
            "counts": {"high": 0, "medium": 0, "low": 0},
        }

        for c in customers:
            stats = self._customer_stats(c.id, now)
            days_since = stats["days_since_last_visit"]
            visits = stats["total_visits"]
            avg_spend = stats["avg_spent"]

            score, level = self._calc_risk_score(days_since, visits, avg_spend)

            if level == "none":
                continue  # skip actively returning customers

            result[level].append({
                "customer_id": c.id,
                "name": c.name,
                "phone": c.phone,
                "car_plate": c.car_plate,
                "car_model": c.car_model,
                "last_visit_days": days_since,
                "total_visits": visits,
                "total_spent": stats["total_spent"],
                "avg_spent": avg_spend,
                "risk_score": round(score, 4),
                "risk_level": level,
            })
            result["counts"][level] += 1

        return result

    def _customer_stats(
        self, customer_id: int, now: datetime
    ) -> dict[str, Any]:
        """Aggregate completed order stats for a single customer."""
        row = (
            self.db.query(
                func.count(WorkOrder.id).label("total_orders"),
                func.coalesce(func.sum(WorkOrder.total_amount), 0).label(
                    "total_spent"
                ),
                func.max(WorkOrder.created_at).label("last_visit"),
            )
            .filter(
                WorkOrder.customer_id == customer_id,
                WorkOrder.status == "completed",
            )
            .first()
        )

        total_orders = row.total_orders or 0
        total_spent = float(row.total_spent or 0)

        last_visit = _ensure_aware(row.last_visit)
        days_since = 999
        if last_visit is not None:
            days_since = max(0, (now - last_visit).days)

        avg_spent = round(total_spent / total_orders, 2) if total_orders > 0 else 0.0

        return {
            "total_visits": total_orders,
            "total_spent": total_spent,
            "avg_spent": avg_spent,
            "days_since_last_visit": days_since,
        }

    def _calc_risk_score(
        self, days_since: int, visits: int, avg_spend: float
    ) -> tuple[float, str]:
        """Calculate churn risk score and determine risk level.

        Returns
        -------
        (score, level)
            ``score`` is a float in [0, 1]; ``level`` is one of
            ``"high"``, ``"medium"``, ``"low"``, ``"none"``.
        """
        # Normalize each component to [0, 1]
        days_component = min(days_since / 365.0, 1.0)
        freq_component = 1.0 - min(visits / 20.0, 1.0)
        spend_component = 1.0 - min(avg_spend, 10000.0) / 10000.0

        score = (
            days_component * 0.5 + freq_component * 0.3 + spend_component * 0.2
        )
        score = max(0.0, min(1.0, score))

        # Level is based purely on recency threshold
        if days_since > 90:
            level = "high"
        elif days_since > 60:
            level = "medium"
        elif days_since > 30:
            level = "low"
        else:
            level = "none"

        return score, level

    # ── 2. 保养推荐 ─────────────────────────────────────

    def get_maintenance_schedule(self, customer_id: int) -> dict[str, Any]:
        """Calculate due / upcoming maintenance services for a customer.

        Compares the customer's current mileage and time since last service
        against each maintenance interval rule. Returns an ordered list of
        recommendations sorted by most overdue first.

        Parameters
        ----------
        customer_id : int
            Target customer primary key.

        Returns
        -------
        dict
            Customer info and a ``"recommendations"`` list, each entry
            containing ``service``, ``description``, ``overdue_ratio``,
            ``status`` (``"overdue"`` / ``"due_soon"`` / ``"upcoming"`` /
            ``"ok"``) and ``urgency``.

        Raises
        ------
        ValueError
            If no customer with *customer_id* exists.
        """
        customer = (
            self.db.query(Customer)
            .filter(Customer.id == customer_id)
            .first()
        )
        if not customer:
            raise ValueError(f"客户不存在: {customer_id}")

        now = datetime.now(timezone.utc)
        current_mileage = customer.mileage

        # Last completed work order (source of truth for "last service")
        last_order = (
            self.db.query(WorkOrder)
            .filter(
                WorkOrder.customer_id == customer_id,
                WorkOrder.status == "completed",
            )
            .order_by(WorkOrder.created_at.desc())
            .first()
        )

        last_mileage = 0
        last_date: datetime | None = None
        if last_order:
            last_mileage = last_order.mileage or 0
            last_date = _ensure_aware(last_order.created_at)

        # Already-performed maintenance services (skip re-recommending)
        performed = set()
        reminders = (
            self.db.query(ServiceReminder)
            .filter(
                ServiceReminder.customer_id == customer_id,
                ServiceReminder.reminder_type == "maintenance",
            )
            .all()
        )
        for r in reminders:
            performed.add(r.title)

        recommendations: list[dict[str, Any]] = []
        for rule in MAINTENANCE_RULES:
            service = rule["service"]
            interval_km = rule["interval_km"]
            interval_months = rule["interval_months"]

            # km-based overdue ratio
            overdue_km = 0.0
            if interval_km and current_mileage > 0:
                km_since_last = max(0, current_mileage - last_mileage)
                overdue_km = km_since_last / interval_km

            # time-based overdue ratio
            overdue_time = 0.0
            if interval_months and last_date is not None:
                months_since = (now - last_date).days / 30.0
                overdue_time = months_since / interval_months
            elif interval_months and last_date is None:
                # No service history — brand new customer, nothing is due yet
                overdue_time = 0.0

            overdue = max(overdue_km, overdue_time)

            # Determine status & urgency
            if overdue >= 1.0:
                status = "overdue"
                urgency = "high"
            elif overdue >= 0.8:
                status = "due_soon"
                urgency = "medium"
            elif overdue >= 0.5:
                status = "upcoming"
                urgency = "low"
            else:
                status = "ok"
                urgency = "none"

            # Skip if recently performed (< 30% of interval elapsed)
            if service in performed and overdue < 0.3:
                continue

            recommendations.append({
                "service": service,
                "description": rule["description"],
                "interval_km": interval_km,
                "interval_months": interval_months,
                "last_mileage": last_mileage,
                "current_mileage": current_mileage,
                "km_overdue": round(overdue_km, 2),
                "time_overdue": round(overdue_time, 2),
                "overdue_ratio": round(overdue, 2),
                "status": status,
                "urgency": urgency,
            })

        recommendations.sort(key=lambda r: r["overdue_ratio"], reverse=True)

        return {
            "customer_id": customer_id,
            "name": customer.name,
            "car_plate": customer.car_plate,
            "car_model": customer.car_model,
            "current_mileage": current_mileage,
            "last_service_mileage": last_mileage,
            "last_service_date": last_date.isoformat() if last_date else None,
            "recommendations": recommendations,
        }

    # ── 3. 回访排序 ─────────────────────────────────────

    def get_visit_priorities(self) -> list[dict[str, Any]]:
        """Rank all active customers by callback priority score.

        Priority formula (weights in parentheses):

        * **Churn risk** × 0.4
        * **Historical spend** (normalised) × 0.3
        * **Activity recency** × 0.2
        * **Pending reminders** (count) × 0.1

        Returns
        -------
        list[dict]
            Customers sorted descending by ``priority_score``. Each entry
            includes a ``score_breakdown`` dict with the four components.
        """
        now = datetime.now(timezone.utc)
        customers = (
            self.db.query(Customer)
            .filter(Customer.is_active == True)
            .all()
        )

        # Pre-fetch pending (un-notified) reminder counts per customer
        reminder_rows = (
            self.db.query(
                ServiceReminder.customer_id,
                func.count(ServiceReminder.id).label("cnt"),
            )
            .filter(
                ServiceReminder.is_active == True,
                ServiceReminder.is_notified == False,
            )
            .group_by(ServiceReminder.customer_id)
            .all()
        )
        reminder_counts: dict[int, int] = {r.customer_id: r.cnt for r in reminder_rows}

        scored: list[dict[str, Any]] = []
        for c in customers:
            stats = self._customer_stats(c.id, now)
            days_since = stats["days_since_last_visit"]
            visits = stats["total_visits"]
            total_spent = stats["total_spent"]
            avg_spend = stats["avg_spent"]

            # 1. Churn risk component (0.4)
            risk_score, risk_level = self._calc_risk_score(
                days_since, visits, avg_spend
            )
            churn_component = risk_score * 0.4

            # 2. Historical spend component (0.3)
            # Normalise by 50000 — high-spenders get more attention
            spend_norm = min(total_spent / 50000.0, 1.0)
            spend_component = spend_norm * 0.3

            # 3. Activity recency component (0.2)
            if days_since <= 30:
                activity_score = 1.0
            elif days_since <= 90:
                activity_score = 0.7
            elif days_since <= 180:
                activity_score = 0.4
            elif days_since <= 365:
                activity_score = 0.2
            else:
                activity_score = 0.0
            activity_component = activity_score * 0.2

            # 4. Pending reminders component (0.1)
            pending = reminder_counts.get(c.id, 0)
            reminder_norm = min(pending / 3.0, 1.0)  # 3+ reminders = full score
            reminder_component = reminder_norm * 0.1

            total_score = (
                churn_component
                + spend_component
                + activity_component
                + reminder_component
            )

            scored.append({
                "customer_id": c.id,
                "name": c.name,
                "phone": c.phone,
                "car_plate": c.car_plate,
                "car_model": c.car_model,
                "total_spent": total_spent,
                "total_visits": visits,
                "last_visit_days": days_since,
                "risk_level": risk_level,
                "risk_score": round(risk_score, 4),
                "pending_reminders": pending,
                "score_breakdown": {
                    "churn": round(churn_component, 4),
                    "spend": round(spend_component, 4),
                    "activity": round(activity_component, 4),
                    "reminders": round(reminder_component, 4),
                },
                "priority_score": round(total_score, 4),
            })

        scored.sort(key=lambda x: x["priority_score"], reverse=True)
        return scored
