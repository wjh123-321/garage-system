"""AI Service - Core orchestrator."""
import json, logging, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from openai import OpenAI
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    """Result metadata from an LLM chat call."""
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""
    duration_ms: int = 0


class LLMClient:
    """OpenAI-compatible LLM client with JSON response helpers.

    Backward-compatible wrapper around the module-level ``call_llm`` function.
    """

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def chat(self, messages: list[dict]) -> str:
        """Call LLM and return raw text response."""
        system = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        result = call_llm(system_prompt=system, user_prompt=user)
        if "error" in result:
            raise Exception(result["error"])
        return json.dumps(result)

    def chat_json(self, messages: list[dict]) -> tuple[dict[str, Any], ChatResult]:
        """Call LLM and parse response as JSON."""
        content = self.chat(messages)
        parsed = json.loads(content)
        return parsed, ChatResult(
            content=content,
            prompt_tokens=parsed.get("_prompt_tokens", 0),
            completion_tokens=parsed.get("_completion_tokens", 0),
            model=parsed.get("_model_used", self.model),
            duration_ms=parsed.get("_latency_ms", 0),
        )

ARK_API_KEY = "ark-1b134190-ce8b-4aba-a0f7-b349445b8c2c-c8e9a"
ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
ARK_MODEL = "doubao-pro-32k-250528"

_client: Optional[OpenAI] = None

def get_llm_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=ARK_API_KEY, base_url=ARK_BASE_URL)
    return _client

def call_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 2000) -> dict:
    client = get_llm_client()
    start = time.time()
    try:
        resp = client.chat.completions.create(
            model=ARK_MODEL,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content
        latency = int((time.time() - start) * 1000)
        logger.info("LLM ok: %dms", latency)
        result = json.loads(content)
        result["_latency_ms"] = latency
        result["_model_used"] = ARK_MODEL
        return result
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        logger.error("LLM fail: %s", e)
        return {"error": str(e), "_latency_ms": latency, "_model_used": ARK_MODEL}

class AIService:
    def __init__(self, db: Session):
        self.db = db
        from .repair_recommender import RepairRecommender
        from .parts_forecaster import PartsForecaster
        from .customer_analyzer import CustomerAnalyzer
        self.repair = RepairRecommender(db)
        self.forecast = PartsForecaster(db)
        self.customer = CustomerAnalyzer(db)

    def recommend_repair(self, request) -> dict: return self.repair.recommend(request)
    def forecast_parts(self, days: int = 30) -> dict: return self.forecast.forecast(days)
    def get_at_risk_customers(self) -> dict: return self.customer.get_at_risk_customers()
    def get_maintenance_schedule(self, customer_id: int) -> dict: return self.customer.get_maintenance_schedule(customer_id)
    def get_dashboard_data(self) -> dict:
        at_risk = self.customer.get_at_risk_customers()
        return {
            "at_risk_count": len(at_risk.get("customers", [])),
            "high_risk_count": at_risk.get("high_risk_count", 0),
            "total_analysed": at_risk.get("total", 0),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
