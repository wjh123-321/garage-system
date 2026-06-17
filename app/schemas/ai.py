"""AI schemas — repair recommendation, part forecast, customer insight.

All request/response Pydantic v2 models with from_attributes=True where applicable.
"""

import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field


# ── 维修推荐 ────────────────────────────────────────────


class SuggestedPart(BaseModel):
    """推荐的单个配件（内嵌于 RepairSuggestion）"""
    part_id: int | None = Field(default=None, description="配件ID")
    part_name: str = Field(..., max_length=128, description="配件名称")
    sku: str = Field(default="", max_length=64, description="SKU编码")
    quantity: int = Field(default=1, ge=1, description="数量")
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2, description="单价")
    in_stock: bool = Field(default=True, description="当前是否有库存")


class RepairSuggestion(BaseModel):
    """单个维修建议"""
    name: str = Field(..., max_length=128, description="维修项目名称")
    item_type: str = Field(
        ..., pattern=r"^(part|labor)$", description="part(换件) / labor(工时)"
    )
    parts: list[SuggestedPart] = Field(
        default_factory=list, description="涉及配件列表"
    )
    labor_hours: float = Field(default=0.0, ge=0, description="预估工时(小时)")
    labor_cost: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2, description="工时费")
    part_cost: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2, description="配件费")
    total_cost: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2, description="合计")
    priority: str = Field(
        default="medium",
        pattern=r"^(critical|high|medium|low|info)$",
        description="优先级",
    )
    reason: str = Field(default="", description="推荐理由")


class RepairRecommendRequest(BaseModel):
    """发起维修推荐的请求"""
    fault_description: str = Field(..., description="故障描述")
    car_model: str = Field(..., max_length=64, description="车型")
    mileage: int = Field(..., ge=0, description="当前里程(km)")
    customer_id: int | None = Field(default=None, description="客户ID")
    car_plate: str | None = Field(default=None, max_length=16, description="车牌号")


class RepairRecommendResponse(BaseModel):
    """维修推荐响应"""
    suggestions: list[RepairSuggestion] = Field(
        default_factory=list, description="维修建议列表"
    )
    total_estimate: Decimal = Field(
        default=Decimal("0.00"), ge=0, decimal_places=2, description="预估总费用"
    )
    model_used: str = Field(default="", description="AI模型名称")
    latency_ms: int = Field(default=0, ge=0, description="推理耗时(毫秒)")


# ── 配件预测 ────────────────────────────────────────────


class PartForecastItem(BaseModel):
    """单个配件预测项"""
    part_id: int = Field(..., description="配件ID")
    part_name: str = Field(default="", max_length=128, description="配件名称")
    sku: str = Field(default="", max_length=64, description="SKU编码")
    category: str = Field(default="", max_length=32, description="分类")
    current_stock: int = Field(0, ge=0, description="当前库存")
    min_stock: int = Field(0, ge=0, description="最低库存预警")
    predicted_demand: int = Field(0, ge=0, description="预测需求量")
    confidence: float = Field(0.0, ge=0, le=1, description="置信度")
    suggested_order: int = Field(0, ge=0, description="建议补货量")
    urgency: str = Field(
        default="normal",
        pattern=r"^(normal|low_stock|critical)$",
        description="紧急程度",
    )


class PartForecastResponse(BaseModel):
    """配件预测响应"""
    forecasts: list[PartForecastItem] = Field(
        default_factory=list, description="预测列表"
    )
    total_parts: int = Field(0, ge=0, description="预测配件总数")
    critical_count: int = Field(0, ge=0, description="紧急补货数量")
    forecast_days: int = Field(0, ge=0, description="预测天数")
    generated_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now, description="生成时间"
    )


# ── 客户流失分析 ──────────────────────────────────────


class AtRiskCustomer(BaseModel):
    """高流失风险客户"""
    customer_id: int = Field(..., description="客户ID")
    name: str = Field(default="", max_length=64, description="客户姓名")
    phone: str = Field(default="", max_length=20, description="手机号")
    car_plate: str = Field(default="", max_length=16, description="车牌号")
    car_model: str = Field(default="", max_length=64, description="车型")
    days_since_last_visit: int = Field(0, ge=0, description="最近到店至今(天)")
    risk_score: float = Field(0.0, ge=0, le=1, description="流失风险分")
    risk_level: str = Field(
        default="low",
        pattern=r"^(low|medium|high|critical)$",
        description="风险等级",
    )
    suggested_action: str = Field(default="", description="推荐运营动作")


class AtRiskResponse(BaseModel):
    """流失风险客户列表响应"""
    customers: list[AtRiskCustomer] = Field(
        default_factory=list, description="风险客户列表"
    )
    total: int = Field(0, ge=0, description="风险客户总数")
    high_risk_count: int = Field(0, ge=0, description="高危客户数")


# ── 保养推荐 ───────────────────────────────────────────


class MaintenanceRecommend(BaseModel):
    """单条保养推荐"""
    service_type: str = Field(
        ..., max_length=32, description="保养类型: oil_change / tire / brake / inspection / etc."
    )
    description: str = Field(default="", description="保养说明")
    due_date: datetime.date | None = Field(default=None, description="建议截止日期")
    due_mileage: int = Field(default=0, ge=0, description="建议截止里程(km)")
    priority: str = Field(
        default="medium",
        pattern=r"^(high|medium|low)$",
        description="优先级",
    )
    based_on: str = Field(
        default="mileage",
        pattern=r"^(mileage|time|both)$",
        description="依据: mileage(里程)/time(时间)/both(两者)",
    )


class CustomerMaintenanceResponse(BaseModel):
    """客户保养推荐响应"""
    customer_id: int = Field(..., description="客户ID")
    customer_name: str = Field(default="", description="客户姓名")
    car_plate: str = Field(default="", max_length=16, description="车牌号")
    car_model: str = Field(default="", max_length=64, description="车型")
    current_mileage: int = Field(0, ge=0, description="当前里程")
    recommendations: list[MaintenanceRecommend] = Field(
        default_factory=list, description="保养建议列表"
    )


# ── 仪表盘 ─────────────────────────────────────────────


class AIDashboardResponse(BaseModel):
    """AI 模块仪表盘聚合数据"""
    repair_hotspots: dict = Field(
        default_factory=dict, description="维修热点分布 {\"category\": count}"
    )
    forecast_alerts: list[dict] = Field(
        default_factory=list, description="预测预警列表"
    )
    at_risk_count: int = Field(0, ge=0, description="流失风险客户总数")
    high_risk_count: int = Field(0, ge=0, description="高危客户数")
    total_analysed: int = Field(0, ge=0, description="已分析客户总数")
    updated_at: datetime.datetime | None = Field(
        default=None, description="数据更新时间"
    )


# ── 反馈 ───────────────────────────────────────────────


class AIFeedbackCreate(BaseModel):
    """提交维修推荐反馈"""
    recommendation_id: int = Field(..., description="推荐记录ID")
    feedback: str = Field(
        ..., pattern=r"^(accept|reject)$", description="反馈: accept(采纳) / reject(拒绝)"
    )
