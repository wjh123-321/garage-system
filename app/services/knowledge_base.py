"""冷启动维修知识库。

当修理厂数据不足（工单数 < 10）时，使用规则引擎代替 LLM 生成维修建议。
包含 8 个系统类别，30+ 维修方案，基于关键词匹配和症状匹配进行推荐。

配件价格参考 2024-2025 年市场行情（综合途虎、京东养车、线下修理厂报价）。
"""

import logging
from typing import Any

logger = logging.getLogger("knowledge_base")

# ── 知识库条目 ─────────────────────────────────────────────

KNOWLEDGE_BASE: list[dict[str, Any]] = [
    # ==============================
    # a) 发动机系统
    # ==============================
    {
        "category": "发动机系统",
        "keywords": ["发动机", "引擎", "异响", "抖动", "缺缸", "加速无力", "启动困难",
                     "水温高", "怠速不稳", "熄火", "动力不足", "发动机故障灯", "亮灯"],
        "symptoms": [
            "发动机运转时有异常噪音",
            "怠速或行驶中车身明显抖动",
            "加速反应迟钝、动力不足",
            "冷车或热车启动困难",
            "水温表指示偏高或开锅",
            "发动机故障灯常亮",
            "行驶中自动熄火",
        ],
        "check_items": [
            "读取发动机故障码 (OBD)",
            "检查机油液位及品质",
            "检查火花塞状况",
            "检查点火线圈工作状态",
            "检查节气门积碳情况",
            "检查冷却液液位及循环",
            "检查进气管路泄漏",
        ],
        "repairs": [
            {
                "name": "发动机常规保养（机油+机滤+空滤）",
                "priority": "medium",
                "reason": "机油老化或脏污导致润滑不足，是最常见的发动机问题来源",
                "estimated_parts": "全合成机油 4L + 机油滤清器 + 空气滤清器",
                "estimated_labor_hours": 0.5,
                "estimated_cost": 580,
            },
            {
                "name": "更换火花塞",
                "priority": "medium",
                "reason": "火花塞电极磨损或积碳导致点火不良，引起抖动和加速无力",
                "estimated_parts": "铱金火花塞 x4",
                "estimated_labor_hours": 0.8,
                "estimated_cost": 460,
            },
            {
                "name": "清洗节气门",
                "priority": "low",
                "reason": "节气门积碳导致怠速不稳、加速响应迟钝",
                "estimated_parts": "节气门清洗剂",
                "estimated_labor_hours": 0.5,
                "estimated_cost": 145,
            },
            {
                "name": "更换点火线圈",
                "priority": "high",
                "reason": "点火线圈老化击穿导致缺缸、抖动严重、故障灯亮",
                "estimated_parts": "点火线圈 + 火花塞",
                "estimated_labor_hours": 1.0,
                "estimated_cost": 620,
            },
        ],
        "warnings": [
            "水温高时严禁继续行驶，可能导致缸垫冲毁或发动机拉缸",
            "发动机故障灯亮时应尽快检修，避免催化转化器损坏",
        ],
        "notes": "发动机维修优先读取故障码，根据故障码定位具体问题，避免盲目换件",
    },

    # ==============================
    # b) 刹车系统
    # ==============================
    {
        "category": "刹车系统",
        "keywords": ["刹车", "制动", "异响", "刹不住", "刹车软", "刹车抖",
                     "刹车片", "刹车盘", "刹车油", "手刹", "ABS", "制动液"],
        "symptoms": [
            "刹车时发出尖锐金属摩擦声",
            "刹车踏板行程变长、感觉软绵",
            "刹车距离明显增加",
            "高速刹车时方向盘或车身抖动",
            "刹车警示灯亮",
            "刹车踏板抖动",
        ],
        "check_items": [
            "检查前后刹车片厚度",
            "检查刹车盘磨损及平整度",
            "检查刹车油液位及含水率",
            "检查刹车管路有无泄漏",
            "检查制动卡钳活动是否正常",
        ],
        "repairs": [
            {
                "name": "更换前刹车片",
                "priority": "high",
                "reason": "前刹车片磨损到极限（厚度 < 3mm），刹车性能大幅下降",
                "estimated_parts": "陶瓷刹车片（前）",
                "estimated_labor_hours": 0.8,
                "estimated_cost": 440,
            },
            {
                "name": "更换后刹车片",
                "priority": "high",
                "reason": "后刹车片磨损到极限，影响制动平衡",
                "estimated_parts": "陶瓷刹车片（后）",
                "estimated_labor_hours": 0.8,
                "estimated_cost": 400,
            },
            {
                "name": "更换刹车盘+刹车片",
                "priority": "high",
                "reason": "刹车盘磨损起槽或变形，导致刹车抖动、异响",
                "estimated_parts": "刹车盘 x2 + 陶瓷刹车片",
                "estimated_labor_hours": 1.5,
                "estimated_cost": 1040,
            },
            {
                "name": "更换刹车油",
                "priority": "medium",
                "reason": "刹车油含水率超标（>3%）导致沸点下降，长下坡时制动失效风险",
                "estimated_parts": "DOT4 刹车油 1L",
                "estimated_labor_hours": 0.5,
                "estimated_cost": 180,
            },
        ],
        "warnings": [
            "刹车片厚度低于 3mm 必须立即更换",
            "刹车油含水率超过 4% 必须更换，否则高温下可能汽化导致刹车失灵",
        ],
        "notes": "建议前后刹车片同时检查，必要时成套更换以保证制动平衡",
    },

    # ==============================
    # c) 空调系统
    # ==============================
    {
        "category": "空调系统",
        "keywords": ["空调", "制冷", "冷气", "暖气", "异味", "出风小", "不制冷",
                     "压缩机", "冷媒", "氟", "AC"],
        "symptoms": [
            "空调出风口吹出的风不冷",
            "开空调有霉味或酸味",
            "出风口风量明显偏小",
            "空调压缩机不工作或频繁启停",
            "空调制冷效果越来越差",
        ],
        "check_items": [
            "检查空调出风口温度",
            "检查空调管路压力",
            "检查空调滤芯状况",
            "检查蒸发箱是否发霉",
            "检查冷凝器是否堵塞",
            "检查压缩机皮带及离合器",
        ],
        "repairs": [
            {
                "name": "空调加氟（补充冷媒）",
                "priority": "medium",
                "reason": "冷媒自然渗漏或不足导致制冷效果差",
                "estimated_parts": "R134a 冷媒",
                "estimated_labor_hours": 1.0,
                "estimated_cost": 220,
            },
            {
                "name": "更换空调滤芯",
                "priority": "low",
                "reason": "空调滤芯过脏堵塞，导致出风小且有异味",
                "estimated_parts": "活性炭空调滤芯",
                "estimated_labor_hours": 0.3,
                "estimated_cost": 125,
            },
            {
                "name": "清洗蒸发箱",
                "priority": "medium",
                "reason": "蒸发箱表面滋生的细菌霉菌是空调异味的根本原因",
                "estimated_parts": "蒸发箱清洗套装",
                "estimated_labor_hours": 1.5,
                "estimated_cost": 420,
            },
        ],
        "warnings": [
            "空调异味可能由蒸发箱霉菌引起，单换滤芯无法根除",
            "冷媒泄漏需找到泄漏点再补充，否则很快又失效",
        ],
        "notes": "建议每年夏季前检查空调系统，更换滤芯并消毒",
    },

    # ==============================
    # d) 变速箱
    # ==============================
    {
        "category": "变速箱",
        "keywords": ["变速箱", "变速器", "波箱", "顿挫", "不走", "异响", "漏油",
                     "挂挡", "换挡", "ATF", "离合器", "CVT", "双离合"],
        "symptoms": [
            "换挡时有明显顿挫或冲击感",
            "挂挡后车辆不走或反应延迟",
            "变速箱区域有异常噪音",
            "变速箱底部有油渍或滴油",
            "变速箱故障灯亮",
            "行驶中突然失去动力",
        ],
        "check_items": [
            "检查变速箱油位及油质",
            "读取变速箱故障码",
            "检查变速箱外部有无漏油",
            "路试感受换挡品质",
            "检查变速箱机脚胶",
        ],
        "repairs": [
            {
                "name": "更换变速箱油 + 滤网",
                "priority": "medium",
                "reason": "变速箱油老化变质导致换挡顿挫、润滑不良",
                "estimated_parts": "ATF 变速箱油 12L + 滤网 + 油底垫",
                "estimated_labor_hours": 1.5,
                "estimated_cost": 810,
            },
            {
                "name": "阀体清洗",
                "priority": "high",
                "reason": "阀体内部油泥堵塞导致换挡延迟、顿挫严重",
                "estimated_parts": "阀体清洗剂 + 变速箱油",
                "estimated_labor_hours": 3.0,
                "estimated_cost": 1190,
            },
        ],
        "warnings": [
            "变速箱故障严重时应立即停驶，拖车进厂，避免内部损坏扩大",
            "严禁不同型号变速箱油混用",
        ],
        "notes": "变速箱维修成本高，建议先做油位检查和故障码读取，避免过度维修",
    },

    # ==============================
    # e) 电气系统
    # ==============================
    {
        "category": "电气系统",
        "keywords": ["电瓶", "蓄电池", "亏电", "打不着", "启动", "发电机",
                     "大灯", "灯光", "灯泡", "电路", "保险丝", "搭铁", "漏电"],
        "symptoms": [
            "车辆停放过夜后无法启动",
            "启动时仪表盘灯光变暗",
            "大灯亮度不足或单侧不亮",
            "发电机异响或充电指示灯亮",
            "车辆有漏电现象",
            "多个电器同时工作异常",
        ],
        "check_items": [
            "测量蓄电池电压及启动电压",
            "测试发电机充电电压",
            "检查全车灯光功能",
            "测量静态放电电流（漏电检测）",
            "检查主保险丝及继电器",
        ],
        "repairs": [
            {
                "name": "更换蓄电池",
                "priority": "high",
                "reason": "蓄电池老化（CCA下降或电压不足）导致启动困难",
                "estimated_parts": "60Ah 免维护蓄电池",
                "estimated_labor_hours": 0.3,
                "estimated_cost": 440,
            },
            {
                "name": "更换发电机总成",
                "priority": "high",
                "reason": "发电机发电量不足或整流器损坏，导致蓄电池持续亏电",
                "estimated_parts": "发电机总成",
                "estimated_labor_hours": 1.5,
                "estimated_cost": 950,
            },
            {
                "name": "更换大灯灯泡",
                "priority": "low",
                "reason": "大灯灯泡寿命到期烧毁，影响夜间行车安全",
                "estimated_parts": "H7 卤素灯泡 x2",
                "estimated_labor_hours": 0.3,
                "estimated_cost": 130,
            },
        ],
        "warnings": [
            "蓄电池寿命一般 3-5 年，超过此期限建议预防性更换",
            "换蓄电池时注意先接正极后接负极，避免短路",
        ],
        "notes": "亏电故障需区分是电池本身问题还是发电机/漏电问题，不可盲目换电瓶",
    },

    # ==============================
    # f) 底盘悬挂
    # ==============================
    {
        "category": "底盘悬挂",
        "keywords": ["底盘", "悬挂", "减震", "避震", "异响", "跑偏", "偏磨",
                     "摆臂", "球头", "平衡杆", "方向机", "胶套", "底盘松散"],
        "symptoms": [
            "过减速带或颠簸路面时底盘异响",
            "车辆行驶中方向跑偏",
            "轮胎内侧或外侧异常磨损",
            "车身侧倾大或晃动",
            "方向盘回正无力",
            "减震器漏油",
        ],
        "check_items": [
            "检查减震器有无漏油",
            "检查下摆臂球头及胶套间隙",
            "检查平衡杆连接杆",
            "检查方向机内/外球头",
            "四轮定位数据检测",
            "检查轮胎磨损均匀性",
        ],
        "repairs": [
            {
                "name": "更换前减震器总成",
                "priority": "medium",
                "reason": "减震器漏油或失效导致车身晃动、轮胎接地不良",
                "estimated_parts": "前减震器总成 x2",
                "estimated_labor_hours": 2.0,
                "estimated_cost": 1100,
            },
            {
                "name": "更换下摆臂总成",
                "priority": "medium",
                "reason": "下摆臂胶套老化开裂导致底盘异响、定位数据偏差",
                "estimated_parts": "下摆臂总成",
                "estimated_labor_hours": 1.5,
                "estimated_cost": 580,
            },
            {
                "name": "四轮定位",
                "priority": "low",
                "reason": "四轮定位数据偏差导致跑偏和轮胎偏磨",
                "estimated_parts": "",
                "estimated_labor_hours": 0.8,
                "estimated_cost": 160,
            },
        ],
        "warnings": [
            "悬挂部件损坏会严重影响行驶安全，发现异响应及时检修",
            "换完悬挂部件后必须做四轮定位",
        ],
        "notes": "底盘异响需路试确认异响来源，通常胶套问题多于金属件断裂",
    },

    # ==============================
    # g) 轮胎
    # ==============================
    {
        "category": "轮胎",
        "keywords": ["轮胎", "胎压", "漏气", "鼓包", "胎噪", "爆胎", "扎钉",
                     "补胎", "动平衡", "换胎", "胎面", "胎壁"],
        "symptoms": [
            "轮胎气压明显下降或完全没气",
            "轮胎侧壁有鼓包或裂纹",
            "行驶中胎噪明显增大",
            "轮胎异常磨损（偏磨、波浪形）",
            "方向盘抖动（特定速度区间）",
            "轮胎扎入钉子或异物",
        ],
        "check_items": [
            "检查轮胎气压及充气状态",
            "检查轮胎胎面磨损深度（花纹深度）",
            "检查轮胎侧壁有无鼓包、裂纹",
            "检查轮胎动平衡状态",
            "检查轮毂有无变形",
        ],
        "repairs": [
            {
                "name": "补胎（蘑菇钉内补）",
                "priority": "high",
                "reason": "轮胎扎钉导致慢漏气，蘑菇钉内补密封可靠",
                "estimated_parts": "蘑菇钉补胎贴",
                "estimated_labor_hours": 0.5,
                "estimated_cost": 140,
            },
            {
                "name": "更换轮胎",
                "priority": "medium",
                "reason": "轮胎磨损到安全线、鼓包或胎壁损伤，存在爆胎风险",
                "estimated_parts": "205/55R16 轮胎 x2",
                "estimated_labor_hours": 1.0,
                "estimated_cost": 1100,
            },
            {
                "name": "轮胎动平衡",
                "priority": "low",
                "reason": "轮胎动平衡失准导致高速方向盘抖动",
                "estimated_parts": "平衡块",
                "estimated_labor_hours": 0.4,
                "estimated_cost": 90,
            },
        ],
        "warnings": [
            "轮胎鼓包或侧壁损伤必须立即更换，存在高速爆胎风险",
            "轮胎花纹深度低于 1.6mm 法定极限必须更换",
        ],
        "notes": "建议每 2 万公里做一次轮胎换位和动平衡，延长轮胎寿命",
    },

    # ==============================
    # h) 常规保养
    # ==============================
    {
        "category": "常规保养",
        "keywords": ["保养", "机油", "机滤", "三滤", "小保养", "大保养",
                     "首保", "二保", "保养到期", "换油"],
        "symptoms": [
            "保养提示灯亮或保养间隔已到",
            "机油寿命提示不足",
            "上次保养后已行驶较长时间/里程",
            "车辆无异常但保养周期已到",
        ],
        "check_items": [
            "核实上次保养时间及里程",
            "检查机油液位及品质",
            "检查空气滤芯、空调滤芯脏污程度",
            "检查火花塞状态（大保养）",
            "检查全车油液液位",
        ],
        "repairs": [
            {
                "name": "小保养（机油 + 机滤）",
                "priority": "medium",
                "reason": "保养周期已到，需更换机油和机油滤清器保证发动机正常润滑",
                "estimated_parts": "全合成机油 4L + 机油滤清器",
                "estimated_labor_hours": 0.5,
                "estimated_cost": 515,
            },
            {
                "name": "大保养（机油 + 三滤 + 火花塞）",
                "priority": "medium",
                "reason": "大保养周期已到，全面更换油液和滤清器，更换火花塞恢复点火性能",
                "estimated_parts": "全合成机油 4L + 机滤 + 空滤 + 空调滤 + 火花塞 x4",
                "estimated_labor_hours": 1.5,
                "estimated_cost": 970,
            },
        ],
        "warnings": [
            "严禁超过保养里程 50% 以上继续行驶，会加速发动机磨损",
            "不同品牌机油不可混加，换油需彻底排放旧油",
        ],
        "notes": "保养提醒客户按时到店，记录上次保养项目和里程，推荐下次保养时间",
    },
]


# ── 匹配函数 ───────────────────────────────────────────────


def match_repairs(fault_description: str, top_n: int = 3) -> list[dict[str, Any]]:
    """将故障描述与知识库进行关键词匹配，返回得分最高的 N 个类别。

    匹配规则：
      - 每个关键词命中 +2 分
      - 每个症状命中 +3 分
      - 同类别下多个命中去重

    Args:
        fault_description: 故障描述文本
        top_n: 返回前 N 个类别（默认 3）

    Returns:
        按得分降序排列的类别列表，每项为
        {category, repairs, score, keywords_matched, symptoms_matched}
    """
    if not fault_description:
        return []

    fault_lower = fault_description.lower()
    scored: list[dict[str, Any]] = []

    for entry in KNOWLEDGE_BASE:
        keyword_hits = 0
        matched_keywords: list[str] = []
        for kw in entry["keywords"]:
            if kw in fault_lower:
                keyword_hits += 2
                matched_keywords.append(kw)

        symptom_hits = 0
        matched_symptoms: list[str] = []
        for sym in entry["symptoms"]:
            if sym in fault_lower:
                symptom_hits += 3
                matched_symptoms.append(sym)

        total_score = keyword_hits + symptom_hits
        if total_score > 0:
            scored.append({
                "category": entry["category"],
                "repairs": entry["repairs"],
                "score": total_score,
                "keywords_matched": matched_keywords,
                "symptoms_matched": matched_symptoms,
                "warnings": entry["warnings"],
                "notes": entry["notes"],
            })

    # 按得分降序排列
    scored.sort(key=lambda x: x["score"], reverse=True)
    result = scored[:top_n]

    logger.info(
        "知识库匹配完成: 故障=\"%s\", 命中=%d 个类别, 前%d=%s",
        fault_description[:50],
        len(scored),
        top_n,
        [r["category"] for r in result],
    )

    return result


def build_kb_response(
    fault_description: str,
    car_model: str = "",
    mileage: int = 0,
) -> dict[str, Any]:
    """根据知识库构建完整的维修推荐响应。

    生成的字典与 LLM 返回格式完全一致，确保调用方无需额外适配。

    Args:
        fault_description: 故障描述
        car_model: 车型（可选，仅用于分析文本）
        mileage: 里程数（可选，仅用于分析文本）

    Returns:
        {
            "repairs": [...],
            "risk_warnings": [...],
            "suggested_next_steps": [...],
            "overall_analysis": str,
        }
    """
    # 拼接完整描述用于匹配
    full_text = f"{car_model} {fault_description} 里程{mileage}km" if car_model else fault_description

    matched = match_repairs(full_text, top_n=3)

    if not matched:
        return {
            "repairs": [],
            "risk_warnings": [],
            "suggested_next_steps": ["请提供更详细的故障描述，以便系统为您推荐维修方案"],
            "overall_analysis": "当前故障描述无法匹配知识库中的已知类别，建议人工诊断或补充更多信息。",
        }

    # --- 收集维修方案（去重，按优先级排序） ---
    seen_names: set[str] = set()
    repairs: list[dict[str, Any]] = []
    for cat in matched:
        for r in cat["repairs"]:
            if r["name"] not in seen_names:
                seen_names.add(r["name"])
                repairs.append({
                    "name": r["name"],
                    "priority": r["priority"],
                    "reason": r["reason"],
                    "estimated_parts": r["estimated_parts"],
                    "estimated_labor_hours": r["estimated_labor_hours"],
                    "estimated_cost": r["estimated_cost"],
                })

    # 按优先级排序
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    repairs.sort(key=lambda r: priority_order.get(r["priority"], 5))

    # --- 收集安全警告（去重） ---
    risk_warnings: list[str] = []
    seen_warnings: set[str] = set()
    for cat in matched:
        for w in cat["warnings"]:
            if w not in seen_warnings:
                seen_warnings.add(w)
                risk_warnings.append(w)

    # --- 生成后续步骤 ---
    suggested_next_steps: list[str] = []
    suggested_next_steps.append("进店进行故障码读取和实车检查，确认具体问题")
    if repairs:
        top = repairs[0]
        suggested_next_steps.append(f"优先处理「{top['name']}」（{top['reason']}）")
    suggested_next_steps.append("完成维修后进行路试验证，确保问题彻底解决")

    # --- 生成总体分析 ---
    categories_str = "、".join(c["category"] for c in matched)
    matched_keywords_total = sum(len(c["keywords_matched"]) for c in matched)
    overall_analysis = (
        f"根据故障描述，系统判断可能涉及「{categories_str}」。"
        f"共匹配到 {matched_keywords_total} 个关键词/症状，"
        f"推荐 {len(repairs)} 项维修方案。"
    )
    if car_model:
        overall_analysis += f" 车型 {car_model}，当前里程 {mileage:,}km。"
    overall_analysis += " 此为冷启动知识库推荐，建议结合实车检查结果确认。"

    return {
        "repairs": repairs,
        "risk_warnings": risk_warnings,
        "suggested_next_steps": suggested_next_steps,
        "overall_analysis": overall_analysis,
    }
