"""AI智能引擎 - 维修推荐、配件预测、流失预警、保养推荐、仪表盘、反馈"""

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.ai_recommendation import AIRepairRecommendation
from ..schemas.ai import (
    AIFeedbackCreate,
    AIDashboardResponse,
    AtRiskCustomer,
    AtRiskResponse,
    CustomerMaintenanceResponse,
    MaintenanceRecommend,
    PartForecastResponse,
    RepairRecommendRequest,
    RepairRecommendResponse,
    SuggestedPart,
    RepairSuggestion,
)
from ..services.ai_service import AIService

logger = logging.getLogger("ai_router")
router = APIRouter(prefix="/api/ai", tags=["AI智能引擎"])

# 故障关键词 -> 通用维修建议（LLM降级备用）
_FALLBACK_REPAIR_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"(刹车|制动|刹车片|刹车盘|abs|刹不住)"), "刹车系统检查", "检查刹车片磨损情况，必要时更换刹车片/刹车盘"),
    (re.compile(r"(发动机|引擎|抖动|怠速|加速无力|熄火)"), "发动机系统诊断", "建议读取故障码，检查火花塞、点火线圈及燃油系统"),
    (re.compile(r"(变速箱|变速器|换挡|顿挫|at|dct|cvt)"), "变速箱系统检查", "检查变速箱油位及油质，读取变速箱故障码"),
    (re.compile(r"(轮胎|胎压|跑偏|抖动|补胎)"), "轮胎检查与动平衡", "检查胎压及轮胎磨损情况，做动平衡或四轮定位"),
    (re.compile(r"(空调|制冷|不冷|暖风|压缩机)"), "空调系统检修", "检查制冷剂压力，清洗冷凝器，必要时更换空调滤芯"),
    (re.compile(r"(底盘|悬挂|减震|异响|过坑)"), "底盘悬挂检查", "检查减震器、摆臂、球头及胶套磨损情况"),
    (re.compile(r"(转向|方向机|方向重|跑偏)"), "转向系统检查", "检查方向机、助力泵及转向拉杆状态"),
    (re.compile(r"(漏水|冷却|高温|开锅|水箱)"), "冷却系统检修", "检查水箱、水管、节温器及水泵，补充防冻液"),
    (re.compile(r"(漏油|机油|渗油)"), "漏油检查", "检查发动机及变速箱密封件，清洁后确认漏点"),
    (re.compile(r"(保养|机油|机滤|三滤|大保|小保)"), "常规保养", "更换机油机滤，检查空滤、空调滤及全车油水"),
    (re.compile(r"(异响|噪音|共振)"), "全车异响诊断", "建议路试听诊，检查底盘、发动机及内饰件"),
    (re.compile(r"(电路|电池|亏电|无法启动|灯光)"), "电路电气检查", "检查蓄电池电压、发电机及启动系统"),
]


def get_ai_service(db: Session = Depends(get_db)) -> AIService:
    """依赖注入 - 创建AI服务实例"""
    return AIService(db)


# ── 1. 维修推荐 ──────────────────────────────────────────────


@router.post(
    "/repair/recommend",
    response_model=RepairRecommendResponse,
    summary="生成维修推荐方案",
    responses={
        200: {"description": "成功返回AI生成的维修建议列表及预估总费用"},
        502: {"description": "AI服务异常，返回降级规则匹配结果"},
    },
)
def repair_recommend(
    request: RepairRecommendRequest,
    ai_svc: AIService = Depends(get_ai_service),
) -> RepairRecommendResponse:
    """根据故障描述和车辆信息生成AI维修推荐方案。

    系统分析故障描述、车型、里程等信息，调用大语言模型生成结构化的
    维修建议列表，包含维修项目、工时费用、配件清单及总费用估算。

    - **LLM正常时**：返回AI生成的结构化维修方案，自动关联配件库存
    - **LLM失效时**：自动降级为关键词规则匹配的通用维修建议
    - **数据源**：结合历史相似工单和经验数据进行推荐

    Args:
        request: 维修推荐请求，包含故障描述、车型、里程等信息

    Returns:
        RepairRecommendResponse
        - **suggestions**: 维修建议列表，每个建议包含项目名称、优先级、工时、费用、配件清单
        - **total_estimate**: 预估总费用（元）
        - **model_used**: 使用的AI模型名称
        - **latency_ms**: 推理耗时（毫秒）
    """
    try:
        result = ai_svc.recommend_repair(request)
        suggestions = _parse_suggestions(result.get("suggestions", []))
        return RepairRecommendResponse(
            suggestions=suggestions,
            total_estimate=Decimal(str(result.get("total_estimate", 0))),
            model_used=result.get("model_used", "unknown"),
            latency_ms=result.get("latency_ms", 0),
        )
    except Exception as exc:
        logger.warning("LLM维修推荐失败，降级为规则匹配: %s", exc)
        try:
            degraded = _fallback_repair(request)
            return RepairRecommendResponse(
                suggestions=degraded["suggestions"],
                total_estimate=degraded["total_estimate"],
                model_used="rule-fallback",
                latency_ms=0,
            )
        except Exception as fallback_err:
            logger.error("降级规则匹配也失败: %s", fallback_err)
            raise HTTPException(502, f"AI服务异常: {str(exc)}")


# ── 2. 配件预测 ──────────────────────────────────────────────


@router.get(
    "/parts/forecast",
    response_model=PartForecastResponse,
    summary="配件需求预测",
    responses={
        200: {"description": "成功返回配件预测数据，包含预测需求量及建议补货量"},
        502: {"description": "AI服务异常，无法生成配件预测"},
    },
)
def parts_forecast(
    days: int = Query(30, ge=7, le=180, description="预测天数（7-180天）"),
    ai_svc: AIService = Depends(get_ai_service),
) -> PartForecastResponse:
    """基于历史消耗数据和库存水平预测未来配件需求。

    使用4周加权移动平均算法分析过去90天的配件消耗趋势，
    为每款配件输出预测需求量、建议补货量和紧急程度。

    - **预测算法**：4周加权移动平均（近期权重更高）
    - **紧急程度**：critical(紧急补货) / low_stock(建议补货) / normal(正常)
    - **适用场景**：库存补货计划、采购预算编制

    Args:
        days: 预测天数，默认30天，最长180天

    Returns:
        PartForecastResponse
        - **forecasts**: 配件预测列表，每项包含预测需求量、置信度、建议补货量、紧急程度
        - **total_parts**: 预测配件总数
        - **critical_count**: 紧急补货配件数量
        - **forecast_days**: 预测天数
        - **generated_at**: 生成时间
    """
    try:
        return ai_svc.forecast_parts(days=days)
    except Exception as e:
        logger.error("配件预测失败: %s", e)
        raise HTTPException(502, f"AI服务异常: {str(e)}")


# ── 3. 流失预警 ──────────────────────────────────────────────


@router.get(
    "/customers/at-risk",
    response_model=AtRiskResponse,
    summary="客户流失风险分析",
    responses={
        200: {"description": "成功返回流失风险客户列表及风险等级"},
        502: {"description": "AI服务异常，无法分析客户流失风险"},
    },
)
def customers_at_risk(
    ai_svc: AIService = Depends(get_ai_service),
) -> AtRiskResponse:
    """识别有流失风险的客户并计算风险评分。

    基于客户的最近到店时间、到店频率和消费金额三个维度计算流失风险得分：

    - **high**（高危）：超过90天未到店，流失概率高，需要立即回访
    - **medium**（中危）：60-90天未到店，需要关注并发送提醒
    - **low**（低危）：30-60天未到店，常规维护即可

    评分公式：天数分量 x 0.5 + 频率分量 x 0.3 + 消费分量 x 0.2

    Returns:
        AtRiskResponse
        - **customers**: 风险客户列表，包含客户信息、风险评分、风险等级、建议运营动作
        - **total**: 风险客户总数
        - **high_risk_count**: 高危客户数（risk_level=high）
    """
    try:
        result = ai_svc.get_at_risk_customers()
        return _build_at_risk_response(result)
    except Exception as e:
        logger.error("流失预警分析失败: %s", e)
        raise HTTPException(502, f"AI服务异常: {str(e)}")


# ── 4. 保养推荐 ──────────────────────────────────────────────


@router.get(
    "/customers/{customer_id}/maintenance",
    response_model=CustomerMaintenanceResponse,
    summary="客户保养推荐",
    responses={
        200: {"description": "成功返回客户个性化保养建议列表"},
        404: {"description": "指定客户不存在"},
        502: {"description": "AI服务异常，无法生成保养建议"},
    },
)
def customer_maintenance(
    customer_id: int,
    ai_svc: AIService = Depends(get_ai_service),
) -> CustomerMaintenanceResponse:
    """根据客户车辆信息生成个性化保养建议。

    系统根据客户的车型、当前里程、历史保养记录，结合保养间隔规则库，
    输出逾期/即将到期/未来的保养项目清单，按紧急程度排序。

    - **overdue**（逾期）：已超过保养周期，建议立即安排进店
    - **due_soon**（即将到期）：超过80%保养间隔
    - **upcoming**（需关注）：超过50%保养间隔
    - **ok**（正常）：未到保养周期

    保养规则涵盖：常规保养、机油、刹车片、轮胎、变速箱油、防冻液、空调滤芯等。

    Args:
        customer_id: 客户ID

    Returns:
        CustomerMaintenanceResponse
        - **customer_id**: 客户ID
        - **customer_name**: 客户姓名
        - **car_plate**: 车牌号
        - **car_model**: 车型
        - **current_mileage**: 当前里程
        - **recommendations**: 保养建议列表，每项包含保养类型、说明、优先级、依据
    """
    try:
        result = ai_svc.get_maintenance_schedule(customer_id)
        recommendations = _parse_maintenance_recs(result.get("recommendations", []))
        return CustomerMaintenanceResponse(
            customer_id=result.get("customer_id", customer_id),
            customer_name=result.get("name", ""),
            car_plate=result.get("car_plate", ""),
            car_model=result.get("car_model", ""),
            current_mileage=result.get("current_mileage", 0),
            recommendations=recommendations,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error("保养推荐失败 customer=%s: %s", customer_id, e)
        raise HTTPException(502, f"AI服务异常: {str(e)}")


# ── 5. AI仪表盘 ──────────────────────────────────────────────


@router.get(
    "/dashboard",
    response_model=AIDashboardResponse,
    summary="AI模块聚合仪表盘",
    responses={
        200: {"description": "成功返回AI模块关键指标的聚合仪表盘数据"},
        502: {"description": "AI服务异常，无法聚合仪表盘数据"},
    },
)
def ai_dashboard(
    ai_svc: AIService = Depends(get_ai_service),
) -> AIDashboardResponse:
    """AI智能模块的关键指标聚合看板。

    汇总展示以下数据：
    1. **维修热点分布**：按故障类别统计历史维修频次
    2. **配件补货预警**：紧急补货配件列表
    3. **客户流失概览**：风险客户总数和高危客户数

    适合在管理后台仪表盘页面展示，为管理者提供快速决策依据。

    Returns:
        AIDashboardResponse
        - **repair_hotspots**: 维修热点分布图数据（类别 -> 频次）
        - **forecast_alerts**: 需紧急补货的配件列表
        - **at_risk_count**: 存在流失风险的客户总数
        - **high_risk_count**: 高危流失客户数
        - **total_analysed**: 已分析客户总数
        - **updated_at**: 数据更新时间
    """
    try:
        # 维修热点
        hotspots = ai_svc.repair.get_repair_hotspots()

        # 配件预测预警
        forecast_result = ai_svc.forecast.forecast(days=30)
        forecast_alerts: list[dict[str, Any]] = []
        for f in forecast_result.forecasts:
            if f.urgency == "critical":
                forecast_alerts.append({
                    "part_id": f.part_id,
                    "part_name": f.part_name,
                    "current_stock": f.current_stock,
                    "suggested_order": f.suggested_order,
                })

        # 流失风险
        at_risk = ai_svc.get_at_risk_customers()
        counts = at_risk.get("counts", {})

        at_risk_total = counts.get("high", 0) + counts.get("medium", 0) + counts.get("low", 0)
        analysed_total = sum(len(at_risk.get(level, [])) for level in ("high", "medium", "low"))

        return AIDashboardResponse(
            repair_hotspots={h["category"]: h["count"] for h in hotspots},
            forecast_alerts=forecast_alerts,
            at_risk_count=at_risk_total,
            high_risk_count=counts.get("high", 0),
            total_analysed=analysed_total,
            updated_at=datetime.now(timezone.utc),
        )
    except Exception as e:
        logger.error("AI仪表盘数据聚合失败: %s", e)
        raise HTTPException(502, f"AI服务异常: {str(e)}")


# ── 6. 推荐反馈 ──────────────────────────────────────────────


@router.post(
    "/feedback",
    summary="提交推荐反馈",
    responses={
        200: {"description": "反馈提交成功"},
        404: {"description": "推荐的工单或分析记录不存在"},
        502: {"description": "AI服务异常，无法保存反馈"},
    },
)
def submit_feedback(
    body: AIFeedbackCreate,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """对AI推荐结果提交采纳/拒绝反馈，用于持续优化推荐质量。

    记录用户对某条AI推荐结果的反馈（accept 采纳 / reject 拒绝），
    帮助系统评估推荐准确率并持续改进算法。

    Args:
        body: AIFeedbackCreate
            - **recommendation_id**: 推荐记录ID（必填）
            - **feedback**: 反馈类型（accept 采纳 / reject 拒绝）

    Returns:
        dict
        - **id**: 推荐记录ID
        - **feedback**: 更新后的反馈状态
        - **message**: 操作结果消息
    """
    try:
        rec = db.query(AIRepairRecommendation).filter(
            AIRepairRecommendation.id == body.recommendation_id
        ).first()
        if not rec:
            raise HTTPException(404, "推荐记录不存在")

        rec.feedback = body.feedback
        db.commit()

        logger.info("推荐反馈已提交 id=%s feedback=%s", rec.id, rec.feedback)
        return {
            "id": rec.id,
            "feedback": rec.feedback,
            "message": "反馈提交成功",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("反馈保存失败: %s", e)
        raise HTTPException(502, f"AI服务异常: {str(e)}")


# ── 内部辅助函数 ─────────────────────────────────────────────


def _parse_suggestions(suggestions_data: list[dict[str, Any]]) -> list[RepairSuggestion]:
    """将原始建议字典列表转换为 RepairSuggestion Pydantic 模型列表。

    Args:
        suggestions_data: 从服务层返回的原始建议数据

    Returns:
        规范化后的 RepairSuggestion 列表
    """
    result: list[RepairSuggestion] = []
    for s in suggestions_data:
        if not isinstance(s, dict):
            continue
        parts = [
            SuggestedPart(
                part_id=p.get("part_id"),
                part_name=str(p.get("part_name", "")),
                sku=str(p.get("sku", "")),
                quantity=int(p.get("quantity", 1)),
                unit_price=Decimal(str(p.get("estimated_price", p.get("unit_price", 0)))),
                in_stock=bool(p.get("in_stock", True)),
            )
            for p in s.get("parts", [])
            if isinstance(p, dict)
        ]
        result.append(
            RepairSuggestion(
                name=str(s.get("name", "")),
                item_type=str(s.get("item_type", "part" if parts else "labor")),
                parts=parts,
                labor_hours=float(s.get("labor_hours", 0)),
                labor_cost=Decimal(str(s.get("labor_cost", 0))),
                part_cost=Decimal(str(s.get("part_cost", 0))),
                total_cost=Decimal(str(s.get("total_cost", 0))),
                priority=str(s.get("priority", "medium")),
                reason=str(s.get("reason", "")),
            )
        )
    return result


def _fallback_repair(request: RepairRecommendRequest) -> dict[str, Any]:
    """LLM 失效时的降级处理：基于关键词匹配返回通用维修建议。

    遍历故障描述文本，匹配预定义的故障关键词规则，
    为每个匹配到的故障类型生成一个通用维修建议项。

    Args:
        request: 原始维修推荐请求

    Returns:
        包含 suggestions 和 total_estimate 的字典
    """
    text = request.fault_description or ""
    suggestions_raw: list[dict[str, Any]] = []
    matched_names: set[str] = set()

    for pattern, name, reason in _FALLBACK_REPAIR_RULES:
        if pattern.search(text):
            if name in matched_names:
                continue
            matched_names.add(name)
            suggestions_raw.append({
                "name": name,
                "item_type": "labor",
                "parts": [],
                "labor_hours": 1.0,
                "labor_cost": Decimal("50.00"),
                "part_cost": Decimal("0.00"),
                "total_cost": Decimal("50.00"),
                "priority": "medium",
                "reason": reason,
            })

    if not suggestions_raw:
        suggestions_raw.append({
            "name": "全车检测",
            "item_type": "labor",
            "parts": [],
            "labor_hours": 0.5,
            "labor_cost": Decimal("30.00"),
            "part_cost": Decimal("0.00"),
            "total_cost": Decimal("30.00"),
            "priority": "low",
            "reason": "建议到店进行专业检测以确认具体故障",
        })

    total_estimate = sum(s["labor_cost"] + s["part_cost"] for s in suggestions_raw)

    return {
        "suggestions": _parse_suggestions(suggestions_raw),
        "total_estimate": total_estimate,
    }


def _build_at_risk_response(result: dict[str, Any]) -> AtRiskResponse:
    """将 customer_analyzer 的原始结果映射为 AtRiskResponse Pydantic 模型。

    Args:
        result: CustomerAnalyzer.get_at_risk_customers() 的返回结果

    Returns:
        规范化的 AtRiskResponse 对象
    """
    action_map: dict[str, str] = {
        "high": "立即电话回访，发送专属优惠券进行召回",
        "medium": "发送保养提醒短信，推送限时优惠活动",
        "low": "定期推送用车知识和会员福利",
        "critical": "紧急处理，主管亲自回访并赠送大额优惠",
    }

    customers: list[AtRiskCustomer] = []
    high_risk_count = 0

    for level in ("high", "medium", "low"):
        for c in result.get(level, []):
            risk_level = c.get("risk_level", level)
            if risk_level == "high":
                high_risk_count += 1
            customers.append(
                AtRiskCustomer(
                    customer_id=int(c["customer_id"]),
                    name=str(c.get("name", "")),
                    phone=str(c.get("phone", "")),
                    car_plate=str(c.get("car_plate", "")),
                    car_model=str(c.get("car_model", "")),
                    days_since_last_visit=int(c.get("last_visit_days", 0)),
                    risk_score=float(c.get("risk_score", 0.0)),
                    risk_level=risk_level,
                    suggested_action=action_map.get(risk_level, "保持常规维护"),
                )
            )

    return AtRiskResponse(
        customers=customers,
        total=len(customers),
        high_risk_count=high_risk_count,
    )


def _parse_maintenance_recs(recs_data: list[dict[str, Any]]) -> list[MaintenanceRecommend]:
    """将 customer_analyzer 的保养推荐原始数据映射为 MaintenanceRecommend 列表。

    Args:
        recs_data: CustomerAnalyzer.get_maintenance_schedule() 的 recommendations 列表

    Returns:
        规范化后的 MaintenanceRecommend 列表
    """
    priority_map: dict[str, str] = {
        "overdue": "high",
        "due_soon": "high",
        "upcoming": "medium",
        "ok": "low",
    }

    result: list[MaintenanceRecommend] = []
    for r in recs_data:
        status = r.get("status", "ok")
        km_overdue = r.get("km_overdue", 0)
        time_overdue = r.get("time_overdue", 0)

        if km_overdue > 0 and time_overdue > 0:
            based_on = "both"
        elif km_overdue > 0:
            based_on = "mileage"
        else:
            based_on = "time"

        result.append(
            MaintenanceRecommend(
                service_type=_normalize_service_type(str(r.get("service", ""))),
                description=str(r.get("description", "")),
                due_mileage=int(r.get("current_mileage", 0)),
                priority=priority_map.get(status, "low"),
                based_on=based_on,
            )
        )

    return result


def _normalize_service_type(service_name: str) -> str:
    """将中文保养名称映射为英文 service_type 标识。

    Args:
        service_name: 中文保养名称（如"常规保养"）

    Returns:
        规范化后的英文 type 标识
    """
    mapping: dict[str, str] = {
        "常规保养": "oil_change",
        "机油": "oil_change",
        "刹车片": "brake",
        "轮胎": "tire",
        "变速箱油": "transmission_fluid",
        "防冻液": "coolant",
        "空调滤芯": "cabin_filter",
    }
    return mapping.get(service_name, service_name.lower().replace(" ", "_"))
