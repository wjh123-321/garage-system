"""AI domain-specific models.

Three tables:
- ai_repair_recommendations: per-session repair diagnostics
- ai_part_forecasts: demand forecasting for parts inventory
- ai_customer_insights: churn-risk & next-best-action per customer
"""

import datetime
from sqlalchemy import (
    String, Integer, Float, DateTime, Date, Text, ForeignKey, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class AIRepairRecommendation(Base):
    """AI-generated repair recommendation per session."""
    __tablename__ = "ai_repair_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True, comment="客户ID"
    )
    car_plate: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True, comment="车牌号"
    )
    car_model: Mapped[str] = mapped_column(
        String(64), default="", comment="车型"
    )
    fault_description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="故障描述"
    )
    mileage: Mapped[int] = mapped_column(
        Integer, default=0, comment="当前里程(km)"
    )
    recommendation_json: Mapped[str] = mapped_column(
        Text, nullable=False, comment="AI推荐结果(结构化JSON字符串)"
    )
    total_estimate: Mapped[float] = mapped_column(
        Float, default=0.0, comment="预估总费用(元)"
    )
    model_used: Mapped[str] = mapped_column(
        String(64), default="", comment="AI模型名称"
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer, default=0, comment="推理耗时(毫秒)"
    )
    feedback: Mapped[str] = mapped_column(
        String(16), default="pending", comment="反馈: pending / accept / reject"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    def __repr__(self) -> str:
        return f"<AIRepairRecommendation {self.car_plate} [{self.feedback}]>"


class AIPartForecast(Base):
    """AI-driven part demand forecast."""
    __tablename__ = "ai_part_forecasts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    part_id: Mapped[int] = mapped_column(
        ForeignKey("parts.id"), nullable=False, index=True, comment="配件ID"
    )
    forecast_date: Mapped[datetime.date] = mapped_column(
        Date, nullable=False, comment="预测对应日期"
    )
    predicted_demand: Mapped[int] = mapped_column(
        Integer, default=0, comment="预测需求量"
    )
    confidence: Mapped[float] = mapped_column(
        Float, default=0.0, comment="置信度 0.0 ~ 1.0"
    )
    current_stock: Mapped[int] = mapped_column(
        Integer, default=0, comment="当前库存量"
    )
    suggested_order: Mapped[int] = mapped_column(
        Integer, default=0, comment="建议补货量"
    )
    method: Mapped[str] = mapped_column(
        String(32), default="", comment="预测方法: arima / prophet / llm / etc."
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )

    part = relationship("Part", viewonly=True)

    def __repr__(self) -> str:
        return f"<AIPartForecast part={self.part_id} demand={self.predicted_demand}>"


class AICustomerInsight(Base):
    """Per-customer churn-risk analysis and next-best-action."""
    __tablename__ = "ai_customer_insights"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), unique=True, nullable=False, index=True,
        comment="客户ID(唯一)"
    )
    risk_score: Mapped[float] = mapped_column(
        Float, default=0.0, comment="流失风险分 0.0 ~ 1.0"
    )
    risk_level: Mapped[str] = mapped_column(
        String(16), default="low", comment="风险等级: low / medium / high / critical"
    )
    days_since_last_visit: Mapped[int] = mapped_column(
        Integer, default=0, comment="最近到店至今(天)"
    )
    total_visits: Mapped[int] = mapped_column(
        Integer, default=0, comment="累计到店次数"
    )
    avg_monthly_visits: Mapped[float] = mapped_column(
        Float, default=0.0, comment="月均到店次数"
    )
    recommended_action: Mapped[str] = mapped_column(
        Text, default="", comment="推荐运营动作"
    )
    next_best_service: Mapped[str] = mapped_column(
        Text, default="", comment="最佳推荐服务"
    )
    analyzed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="分析时间"
    )

    customer = relationship("Customer", viewonly=True)

    def __repr__(self) -> str:
        return f"<AICustomerInsight cust={self.customer_id} risk={self.risk_level}>"
