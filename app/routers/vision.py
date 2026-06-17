"""AI视觉识别路由 - 图片识别汽车故障。

降级阶段：关键词匹配占位。
TODO: 接入火山引擎方舟视觉模型（Seedreal / Doubao-vision）替换降级逻辑。
"""

import base64
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vision", tags=["AI视觉"])


class AnalyzeRequest(BaseModel):
    image_base64: str


class AnalyzeResponse(BaseModel):
    labels: list[str]
    description: str
    confidence: float


# 常见汽车故障关键词库（降级匹配用，后续视觉模型接入后移除）
_FAULT_KEYWORDS: dict[str, list[str]] = {
    "engine": ["发动机", "引擎", "engine", "check engine"],
    "brake": ["刹车", "制动", "brake", "abs"],
    "battery": ["电池", "电瓶", "battery", "亏电"],
    "tire": ["轮胎", "胎压", "tire", "tyre", "爆胎"],
    "oil": ["机油", "漏油", "oil", "leak"],
    "coolant": ["冷却液", "水温", "coolant", "overheat", "开锅"],
    "transmission": ["变速箱", "变速器", "transmission", "顿挫"],
    "light": ["大灯", "车灯", "灯光", "headlight", "tail light"],
    "exhaust": ["排气管", "尾气", "exhaust", "冒烟"],
    "suspension": ["悬挂", "减震", "避震", "suspension"],
}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_image(req: AnalyzeRequest):
    """接收车辆故障图片base64，识别故障类型。

    当前为降级实现：针对base64原文做关键词匹配。
    TODO: 替换为火山引擎方舟视觉模型API调用，返回真实视觉识别结果。
    """
    if not req.image_base64 or len(req.image_base64) < 100:
        raise HTTPException(status_code=400, detail="无效的图片数据")

    # 解码校验base64合法性
    try:
        image_data = base64.b64decode(req.image_base64)
        logger.info("收到图片识别请求, 大小: %d bytes, 长度: %d chars",
                    len(image_data), len(req.image_base64))
    except (ValueError, Exception):
        raise HTTPException(status_code=400, detail="图片base64编码无效")

    # ═══════════════════════════════════════════════════════
    # 降级：关键词匹配（视觉模型接入后替换此区块）
    # ═══════════════════════════════════════════════════════
    try:
        # 在base64原文（前5000字符）中搜索已知故障关键词
        haystack = req.image_base64[:5000].lower()
        matched_labels: list[str] = []
        for fault_type, keywords in _FAULT_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in haystack:
                    matched_labels.append(fault_type)
                    break

        if matched_labels:
            # 去重并保持顺序
            seen: set[str] = set()
            labels: list[str] = []
            for label in matched_labels:
                if label not in seen:
                    seen.add(label)
                    labels.append(label)
            description = f"检测到可能的故障类型: {', '.join(labels)}"
            confidence = 0.35  # 降级匹配置信度较低
        else:
            labels = []
            description = "未识别到已知故障特征，请上传清晰的车辆故障部位照片"
            confidence = 0.05
    except Exception as e:
        logger.warning("关键词匹配异常: %s", e)
        labels = []
        description = "识别过程异常，请重试"
        confidence = 0.0
    # ═══════════════════════════════════════════════════════
    # 降级结束
    # ═══════════════════════════════════════════════════════

    return AnalyzeResponse(labels=labels, description=description, confidence=confidence)
