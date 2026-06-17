"""Parts demand forecaster using weighted moving average.

Reads consumption history (inventory_transactions WHERE type='out'),
applies a 4-week weighted moving average (weights 0.4/0.3/0.2/0.1),
and produces per-part predictions with restocking suggestions and
urgency grading.
"""

import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.part import Part, InventoryTransaction
from ..schemas.ai import PartForecastItem, PartForecastResponse


class PartsForecaster:
    """Forecast parts demand using a 4-week weighted moving average.

    The pipeline:
        1. Fetch consumption (type='out') from the last 90 days.
        2. Group into 4 weekly buckets, apply weights [0.4, 0.3, 0.2, 0.1].
        3. Project weekly average to the requested forecast horizon.
        4. Combine with current stock / min_stock for restocking advice.
        5. Assign urgency: critical / low_stock / normal.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── public API ────────────────────────────────────────────

    def forecast(self, days: int = 30) -> PartForecastResponse:
        """Run the full forecast pipeline.

        Args:
            days: Forecast horizon in days (default 30, also supports 7).

        Returns:
            PartForecastResponse with one entry per active part.
        """
        history = self._get_consumption_history(days=90)
        predictions = self._calc_moving_average(history, days)

        # Fetch all active parts so even parts with zero history appear
        stmt = select(Part).where(Part.is_active == True)
        parts_result = self.db.execute(stmt)
        all_parts = {p.id: p for p in parts_result.scalars().all()}

        forecast_items: list[PartForecastItem] = []
        critical_count = 0

        for pid, part in all_parts.items():
            predicted_demand = predictions.get(pid, 0)
            urgency = self._calc_urgency(
                part.quantity, part.min_stock, predicted_demand
            )

            suggested_order = self._calc_suggested_order(
                part.quantity, part.min_stock, predicted_demand, urgency
            )
            if urgency == "critical":
                critical_count += 1

            forecast_items.append(
                PartForecastItem(
                    part_id=pid,
                    part_name=part.name,
                    sku=part.sku,
                    category=part.category,
                    current_stock=part.quantity,
                    min_stock=part.min_stock,
                    predicted_demand=predicted_demand,
                    confidence=0.0,
                    suggested_order=suggested_order,
                    urgency=urgency,
                )
            )

        return PartForecastResponse(
            forecasts=forecast_items,
            total_parts=len(forecast_items),
            critical_count=critical_count,
            forecast_days=days,
            generated_at=datetime.datetime.now(datetime.timezone.utc),
        )

    # ── internal helpers ──────────────────────────────────────

    def _get_consumption_history(self, days: int = 90) -> list[InventoryTransaction]:
        """Return all 'out' transactions from the last *days*."""
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
            days=days
        )
        stmt = (
            select(InventoryTransaction)
            .where(
                InventoryTransaction.type == "out",
                InventoryTransaction.created_at >= cutoff,
            )
            .order_by(InventoryTransaction.created_at)
        )
        return list(self.db.execute(stmt).scalars().all())

    def _calc_moving_average(
        self, history: list[InventoryTransaction], days: int
    ) -> dict[int, int]:
        """4-week weighted moving average.

        Buckets consumption into the most recent 4 weeks (week 0 = 0-7 days
        ago, week 1 = 7-14, ..., week 3 = 21-28), applies weights
        [0.4, 0.3, 0.2, 0.1], converts the weighted weekly sum to a daily
        average, and scales to the requested forecast horizon.

        Returns:
            dict[part_id, predicted_demand]  (>= 0, rounded to int).
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        weights = [0.4, 0.3, 0.2, 0.1]

        # weekly_buckets[week_idx][part_id] = total consumed
        weekly_buckets: list[dict[int, int]] = [{} for _ in range(4)]

        for tx in history:
            age_days = (now - tx.created_at).total_seconds() / 86400.0
            if age_days >= 28:
                continue  # outside the 4-week window
            week_idx = int(age_days // 7)
            if week_idx >= 4:
                continue
            weekly_buckets[week_idx][tx.part_id] = (
                weekly_buckets[week_idx].get(tx.part_id, 0) + tx.quantity
            )

        # Collect every part that appears in any bucket
        all_part_ids: set[int] = set()
        for bucket in weekly_buckets:
            all_part_ids.update(bucket.keys())

        predictions: dict[int, int] = {}
        for pid in all_part_ids:
            weighted_sum = 0.0
            for week_idx in range(4):
                qty = weekly_buckets[week_idx].get(pid, 0)
                weighted_sum += qty * weights[week_idx]

            # Weighted weekly total -> daily average -> scale to forecast days
            daily_avg = weighted_sum / 7.0
            predicted = round(daily_avg * days)
            predictions[pid] = max(predicted, 0)

        return predictions

    def _get_part_details(self, part_ids: list[int]) -> dict[int, dict]:
        """Batch-fetch Part records by ID.

        Returns:
            dict[part_id, {name, sku, category, quantity, min_stock}].
        """
        if not part_ids:
            return {}
        stmt = select(Part).where(Part.id.in_(part_ids))
        parts = list(self.db.execute(stmt).scalars().all())
        return {
            p.id: {
                "name": p.name,
                "sku": p.sku,
                "category": p.category,
                "quantity": p.quantity,
                "min_stock": p.min_stock,
            }
            for p in parts
        }

    def _calc_urgency(self, stock: int, min_stock: int, demand: int) -> str:
        """Classify urgency for a single part.

        Rules (in order):
            - ``"critical"``   -- stock <= min_stock AND demand > 0
            - ``"low_stock"``  -- stock - demand <= min_stock
            - ``"normal"``     -- otherwise
        """
        if stock <= min_stock and demand > 0:
            return "critical"
        if stock - demand <= min_stock:
            return "low_stock"
        return "normal"

    # ── private helpers ───────────────────────────────────────

    @staticmethod
    def _calc_suggested_order(
        stock: int, min_stock: int, demand: int, urgency: str
    ) -> int:
        """Derive the recommended order quantity.

        For **critical** and **low_stock** the recommendation brings stock
        up to ``demand + min_stock``.  ``normal`` urgency returns 0.
        """
        if urgency in ("critical", "low_stock"):
            return max(demand + min_stock - stock, 0)
        return 0
