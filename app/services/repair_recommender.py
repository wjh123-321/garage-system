"""Repair recommendation service.

Accepts a fault description + vehicle context, retrieves similar historical
work orders via ILIKE keyword matching, calls Volcengine Ark LLM (JSON mode)
to generate structured repair suggestions, enriches part data from inventory,
and persists the result.
"""

import json
import logging
import re
import time
from decimal import Decimal
from typing import Any

from openai import OpenAI
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import settings
from ..models.ai_recommendation import AIRepairRecommendation
from ..models.part import Part
from ..models.work_order import WorkOrder
from ..schemas.ai import RepairRecommendRequest

logger = logging.getLogger("repair_recommender")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """你是一个资深汽车维修专家，有20年一线维修经验。根据车辆信息和故障描述，推荐最合理的维修方案。
要求区分必修项和建议项，每个项目标注工时和费用。涉及配件要给名称和预估单价。
输出JSON格式: {suggestions: [{name, priority, reason, parts[{part_name, quantity, estimated_price}], labor_hours, labor_cost, part_cost}], total_estimate, warnings[], notes}"""

_STOPWORDS: frozenset[str] = frozenset({
    "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "什么",
    "车", "汽车", "车辆", "感觉", "有点", "一下", "已经", "还是", "可以",
    "问题", "情况", "检查", "看看", "需要", "请问", "帮忙", "师傅",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "i", "you", "he", "she", "it",
    "we", "they", "this", "that", "these", "those", "my", "your", "his",
    "her", "its", "our", "their", "and", "or", "but", "if", "because",
    "when", "while", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "to", "from",
    "up", "down", "in", "out", "on", "off", "over", "under", "again",
    "further", "then", "once", "here", "there", "not", "no", "so", "very",
    "just", "also", "more", "some", "any", "each", "every", "both", "few",
    "own",
})

_CATEGORY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(刹车|制动|刹车片|刹车盘|abs)"), "制动系统"),
    (re.compile(r"(发动机|引擎|抖动|怠速|加速|机油|正时)"), "发动机系统"),
    (re.compile(r"(变速箱|变速器|换挡|离合|at|dct|cvt)"), "变速箱系统"),
    (re.compile(r"(轮胎|胎压|轮毂|补胎|动平衡)"), "轮胎轮毂"),
    (re.compile(r"(空调|制冷|暖风|压缩机|冷媒)"), "空调系统"),
    (re.compile(r"(底盘|悬挂|减震|避震|摆臂|球头)"), "底盘悬挂"),
    (re.compile(r"(转向|方向机|助力泵|方向)"), "转向系统"),
    (re.compile(r"(电路|电池|发电机|起动机|灯光|喇叭|bcm)"), "电路电气"),
    (re.compile(r"(保养|机油|机滤|空滤|三滤|小保|大保)"), "定期保养"),
    (re.compile(r"(冷却|水箱|风扇|节温器|防冻液)"), "冷却系统"),
    (re.compile(r"(排气|三元|氧传感器|催化)"), "排气系统"),
    (re.compile(r"(车身|喷漆|钣金|保险杠|车门|玻璃)"), "车身钣喷"),
    (re.compile(r"(油路|喷油嘴|燃油泵|汽油滤)"), "燃油系统"),
    (re.compile(r"(异响|噪音|共振)"), "异响诊断"),
]


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RepairRecommender:
    """Generate AI-powered repair suggestions for a given fault / vehicle.

    Usage::

        recommender = RepairRecommender(db)
        result = recommender.recommend(request)
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._llm_client: OpenAI | None = None

    # ── Public API ──────────────────────────────────────────────────────

    def recommend(self, request: RepairRecommendRequest) -> dict:
        """Full pipeline: match history, prompt LLM, parse, enrich, persist.

        Args:
            request: User-submitted fault description, car model, mileage,
                     optional customer context.

        Returns:
            Structured dict compatible with ``RepairRecommendResponse``
            containing suggestions, total estimate, model metadata.
        """
        # 1. Find similar historical work orders
        similar_orders = self._find_similar_orders(
            fault=request.fault_description,
            car_model=request.car_model,
        )

        # 2. Build prompt and call LLM
        prompt = self._build_prompt(request, similar_orders)
        llm_resp, model_name, latency_ms = self._call_llm(prompt)

        # 3. Parse the structured result
        result = self._parse_response(llm_resp)

        # 4. Enrich suggested parts with real inventory data
        result["suggestions"] = self._enrich_with_stock(
            result.get("suggestions", []),
            self.db,
        )

        # 5. Recompute total estimate after enrichment
        total_estimate = self._recompute_total(result)

        # 6. Persist
        self._save_recommendation(
            request=request,
            result=result,
            model_used=model_name,
            latency_ms=latency_ms,
            total_estimate=total_estimate,
            db=self.db,
        )

        return {
            "suggestions": result.get("suggestions", []),
            "warnings": result.get("warnings", []),
            "notes": result.get("notes", []),
            "total_estimate": str(total_estimate),
            "model_used": model_name,
            "latency_ms": latency_ms,
        }

    def get_repair_hotspots(self) -> list[dict[str, Any]]:
        """Aggregate common repair categories from completed work orders.

        Returns:
            List of ``{"category": str, "count": int, "percentage": float}``
            sorted descending by frequency, limited to top 15.
        """
        total = (
            self.db.query(func.count(WorkOrder.id))
            .filter(WorkOrder.status == "completed")
            .scalar()
        ) or 1

        rows = (
            self.db.query(WorkOrder.description)
            .filter(
                WorkOrder.status == "completed",
                WorkOrder.description != "",
            )
            .all()
        )

        counts: dict[str, int] = {}
        for (desc,) in rows:
            matched = False
            for pattern, category in _CATEGORY_PATTERNS:
                if pattern.search(desc):
                    counts[category] = counts.get(category, 0) + 1
                    matched = True
                    break
            if not matched and desc.strip():
                counts["其他"] = counts.get("其他", 0) + 1

        hotspots = [
            {
                "category": cat,
                "count": cnt,
                "percentage": round(cnt / total * 100, 1),
            }
            for cat, cnt in sorted(counts.items(), key=lambda x: -x[1])
        ]
        return hotspots[:15]

    # ── Similar-order search ────────────────────────────────────────────

    def _find_similar_orders(
        self,
        fault: str,
        car_model: str,
    ) -> list[WorkOrder]:
        """Retrieve completed work orders whose description matches keywords
        from the fault text (ILIKE), optionally filtered by car model.

        Args:
            fault: Raw fault description text.
            car_model: Target vehicle model (exact match when non-empty).

        Returns:
            Up to 10 matching ``WorkOrder`` rows, newest first.
        """
        keywords = self._extract_keywords(fault)
        if not keywords:
            return []

        query = self.db.query(WorkOrder).filter(
            WorkOrder.status == "completed",
            WorkOrder.description != "",
        )

        # Car model filter (non-empty)
        if car_model:
            query = query.filter(
                func.lower(WorkOrder.car_model) == func.lower(car_model),
            )

        # Build ILIKE OR conditions
        conditions = [
            WorkOrder.description.ilike(f"%{kw}%")
            for kw in keywords
        ]
        query = query.filter(func.or_(*conditions))

        return (
            query
            .order_by(WorkOrder.created_at.desc())
            .limit(10)
            .all()
        )

    # ── Prompt construction ─────────────────────────────────────────────

    def _build_prompt(
        self,
        request: RepairRecommendRequest,
        similar_orders: list[WorkOrder],
    ) -> str:
        """Assemble the user message that goes to the LLM.

        Includes:
        - Vehicle context (model, mileage, plate if available)
        - Fault description
        - Similar historical orders (if any)
        """
        lines: list[str] = ["请根据以下信息提供维修建议。\n"]

        lines.append("【车辆信息】")
        lines.append(f"  车型: {request.car_model}")
        lines.append(f"  里程: {request.mileage} km")
        if request.car_plate:
            lines.append(f"  车牌: {request.car_plate}")
        lines.append("")

        lines.append("【故障描述】")
        lines.append(f"  {request.fault_description}")
        lines.append("")

        if similar_orders:
            lines.append("【相似历史工单参考】")
            for i, order in enumerate(similar_orders, 1):
                items_summary = "; ".join(
                    f"{item.name} x{item.quantity}"
                    for item in order.items
                ) if order.items else "无明细"
                created = (
                    order.created_at.strftime("%Y-%m-%d")
                    if order.created_at else ""
                )
                desc_preview = (
                    order.description[:80] + ("..." if len(order.description) > 80 else "")
                )
                lines.append(
                    f"  {i}. [{created}] {order.car_model} ({order.mileage}km) "
                    f"- {desc_preview} | 项目: {items_summary} | 总价: {order.total_amount}"
                )
            lines.append("")

        lines.append("请严格按JSON格式输出，只包含JSON，不要添加markdown标记。")

        return "\n".join(lines)

    # ── LLM invocation ──────────────────────────────────────────────────

    def _call_llm(self, prompt: str) -> tuple[str, str, int]:
        """Call Volcengine Ark LLM with JSON mode.

        Returns:
            Tuple of (raw_content, model_name, latency_ms).
        """
        client = self._get_client()
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        start = time.monotonic()
        try:
            resp = client.chat.completions.create(
                model=settings.VOLC_ARK_MODEL,
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"},
            )
        except Exception:
            latency = int((time.monotonic() - start) * 1000)
            logger.exception("LLM call failed after %dms", latency)
            raise

        latency = int((time.monotonic() - start) * 1000)
        content = resp.choices[0].message.content or ""
        model_name = resp.model or settings.VOLC_ARK_MODEL

        if resp.usage:
            logger.info(
                "LLM call OK model=%s latency=%dms prompt=%d completion=%d",
                model_name, latency,
                resp.usage.prompt_tokens,
                resp.usage.completion_tokens,
            )

        return content, model_name, latency

    # ── Response parsing ────────────────────────────────────────────────

    def _parse_response(self, llm_resp: str) -> dict[str, Any]:
        """Parse the LLM JSON response with structural validation.

        Ensures the returned dict has the expected top-level keys and
        that ``suggestions`` is always a list.

        Args:
            llm_resp: Raw JSON string from the LLM.

        Returns:
            Normalised dict with keys ``suggestions``, ``warnings``, ``notes``.
        """
        raw: dict[str, Any] = {}
        try:
            raw = json.loads(llm_resp)
        except json.JSONDecodeError:
            # Try to salvage JSON from markdown fences
            cleaned = llm_resp.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[-1]
                cleaned = cleaned.rsplit("```", 1)[0]
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:].strip()
                cleaned = cleaned.rsplit("```", 1)[0]
            try:
                raw = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                logger.error("LLM response is not valid JSON: %s", exc)
                raw = {}

        # Normalise top-level keys
        result: dict[str, Any] = {
            "suggestions": raw.get("suggestions", raw.get("repairs", [])),
            "warnings": raw.get("warnings", raw.get("risk_warnings", [])),
            "notes": raw.get("notes", raw.get("notes", [])),
        }

        # Ensure suggestions is a list of dicts with required fields
        normalised: list[dict[str, Any]] = []
        for s in result["suggestions"]:
            if not isinstance(s, dict):
                continue
            normalised.append({
                "name": str(s.get("name", s.get("item_name", s.get("repair_name", "")))),
                "priority": str(s.get("priority", "medium")),
                "reason": str(
                    s.get("reason", s.get("description", s.get("reasoning", "")))
                ),
                "parts": self._normalise_parts(
                    s.get("parts", s.get("estimated_parts", s.get("parts_list", [])))
                ),
                "labor_hours": self._to_float(s.get("labor_hours", 0)),
                "labor_cost": str(self._to_decimal(s.get("labor_cost", 0))),
                "part_cost": str(
                    self._to_decimal(s.get("part_cost", s.get("parts_cost", 0)))
                ),
            })
        result["suggestions"] = normalised

        return result

    # ── Stock enrichment ────────────────────────────────────────────────

    def _enrich_with_stock(
        self,
        suggestions: list[dict[str, Any]],
        db: Session,
    ) -> list[dict[str, Any]]:
        """Query the ``parts`` table to fill in real prices and stock status
        for each suggested part.

        Mutates and returns the same suggestions list.
        """
        if not suggestions:
            return suggestions

        for suggestion in suggestions:
            parts_list = suggestion.get("parts", [])
            if not parts_list:
                continue

            enriched: list[dict[str, Any]] = []
            for part_entry in parts_list:
                part_name = part_entry.get("part_name", "")
                quantity = int(part_entry.get("quantity", 1))

                db_part: Part | None = (
                    db.query(Part)
                    .filter(
                        Part.is_active.is_(True),
                        func.lower(Part.name) == func.lower(part_name),
                    )
                    .first()
                )

                if db_part:
                    enriched.append({
                        "part_name": db_part.name,
                        "quantity": quantity,
                        "estimated_price": str(db_part.unit_price),
                        "in_stock": db_part.quantity > 0,
                        "stock_qty": db_part.quantity,
                        "part_id": db_part.id,
                        "sku": db_part.sku,
                    })
                else:
                    enriched.append({
                        "part_name": part_name,
                        "quantity": quantity,
                        "estimated_price": str(
                            self._to_decimal(part_entry.get("estimated_price", 0))
                        ),
                        "in_stock": False,
                        "stock_qty": 0,
                    })

            suggestion["parts"] = enriched

            # Recompute part_cost from enriched prices
            part_cost = Decimal("0.00")
            for p in enriched:
                part_cost += (
                    self._to_decimal(p["estimated_price"]) * p["quantity"]
                )
            suggestion["part_cost"] = str(part_cost)

        return suggestions

    # ── Persistence ─────────────────────────────────────────────────────

    def _save_recommendation(
        self,
        request: RepairRecommendRequest,
        result: dict[str, Any],
        model_used: str,
        latency_ms: int,
        total_estimate: Decimal,
        db: Session,
    ) -> AIRepairRecommendation:
        """Persist the recommendation result to ``ai_repair_recommendations``.

        Args:
            request: Original input.
            result: Parsed + enriched suggestion dict.
            model_used: LLM model identifier.
            latency_ms: Inference duration in milliseconds.
            total_estimate: Computed total cost.
            db: Database session.

        Returns:
            The persisted ``AIRepairRecommendation`` row.
        """
        record = AIRepairRecommendation(
            customer_id=request.customer_id,
            car_plate=request.car_plate or "",
            car_model=request.car_model,
            fault_description=request.fault_description,
            mileage=request.mileage,
            recommendation_json=result,
            total_estimate=total_estimate,
            model_used=model_used,
            latency_ms=latency_ms,
            feedback="pending",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        logger.info(
            "Saved AIRepairRecommendation id=%s car_plate=%s total=%s",
            record.id, record.car_plate, record.total_estimate,
        )
        return record

    # ── Internal helpers ────────────────────────────────────────────────

    def _get_client(self) -> OpenAI:
        """Lazy-init the OpenAI-compatible client."""
        if self._llm_client is None:
            self._llm_client = OpenAI(
                api_key=settings.VOLC_ARK_API_KEY,
                base_url=settings.VOLC_ARK_BASE_URL,
                timeout=60,
            )
        return self._llm_client

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Tokenise *text* into meaningful keywords (removes stopwords).

        Returns unique keywords, max 8, min length 2, sorted by length desc
        (longer = more specific).
        """
        tokens = re.findall(r"[\w一-鿿]+", text.lower())
        keywords = sorted(
            {t for t in tokens if t not in _STOPWORDS and len(t) >= 2},
            key=lambda x: (-len(x), x),
        )
        return keywords[:8]

    @staticmethod
    def _normalise_parts(parts_raw: Any) -> list[dict[str, Any]]:
        """Ensure parts is a list of dicts with standard keys."""
        if not parts_raw or not isinstance(parts_raw, list):
            return []
        result: list[dict[str, Any]] = []
        for p in parts_raw:
            if not isinstance(p, dict):
                continue
            result.append({
                "part_name": str(p.get("part_name", p.get("name", ""))),
                "quantity": int(p.get("quantity", 1)),
                "estimated_price": str(
                    p.get("estimated_price", p.get("unit_price", p.get("price", "0")))
                ),
            })
        return result

    @staticmethod
    def _to_float(val: Any) -> float:
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _to_decimal(val: Any) -> Decimal:
        try:
            return Decimal(str(val))
        except (TypeError, ValueError, ArithmeticError):
            return Decimal("0.00")

    @staticmethod
    def _recompute_total(result: dict[str, Any]) -> Decimal:
        """Sum up all suggestion costs after enrichment."""
        total = Decimal("0.00")
        for s in result.get("suggestions", []):
            total += RepairRecommender._to_decimal(s.get("part_cost", 0))
            total += RepairRecommender._to_decimal(s.get("labor_cost", 0))
        return total
