"""配件查询 API router — 基于本地配件知识库 + VIN 识别推荐."""

from fastapi import APIRouter, HTTPException, Query

from ..services.parts_knowledge import (
    query_parts,
    get_brands,
    get_models,
    get_part_detail,
    PARTS_DATABASE,
)
from ..services.vin_service import VinDecoder

router = APIRouter(prefix="/api/parts-store", tags=["配件数据库"])

decoder = VinDecoder()

# VIN 解码返回的品牌名 -> 配件库品牌名映射
_VIN_BRAND_MAP = {
    "上海大众": "大众",
    "一汽-大众": "大众",
    "华晨宝马": "宝马",
    "北京奔驰": "奔驰",
    "一汽丰田": "丰田",
    "广汽丰田": "丰田",
    "广汽本田": "本田",
    "东风本田": "本田",
    "东风日产": "日产",
    "长安福特": "福特",
}


def _map_vin_brand(vin_brand: str) -> str:
    """将 VIN 解码得到的品牌名映射到配件库品牌键."""
    if vin_brand in PARTS_DATABASE:
        return vin_brand
    return _VIN_BRAND_MAP.get(vin_brand, vin_brand)


@router.get("/brands")
def list_brands():
    """获取所有支持的品牌列表."""
    brands = get_brands()
    return {"total": len(brands), "items": brands}


@router.get("/models")
def list_models(brand: str = Query(..., description="品牌名称，如：大众、丰田")):
    """获取指定品牌下的车型列表."""
    models = get_models(brand)
    if not models:
        raise HTTPException(404, f"品牌 '{brand}' 不存在或无可用车型")
    return {"brand": brand, "total": len(models), "items": models}


@router.get("/search")
def search_parts(
    brand: str = Query("", description="品牌名称（可选）"),
    model: str = Query("", description="车型名称（可选）"),
    keyword: str = Query("", description="配件关键词，如：刹车、机油"),
):
    """按品牌、车型、关键词查询配件."""
    result = query_parts(brand=brand, model=model, keyword=keyword)
    return result


@router.get("/detail")
def part_detail(
    brand: str = Query(..., description="品牌名称"),
    model: str = Query(..., description="车型名称"),
    part: str = Query(..., description="配件名称，如：机油滤清器"),
):
    """获取某个配件详情（OE号、推荐品牌、参考价格等）."""
    detail = get_part_detail(brand, model, part)
    if "error" in detail:
        raise HTTPException(404, detail["error"])
    return detail


@router.get("/vin/{vin}")
def recommend_by_vin(vin: str):
    """VIN 识别后自动匹配车型，推荐该车型的全部配件.

    流程：
    1. 用 VinDecoder 解析 VIN
    2. 品牌名映射到配件库
    3. 返回匹配车型的完整配件列表
    """
    vin_upper = vin.strip().upper()

    # 基本校验
    if len(vin_upper) != 17:
        raise HTTPException(400, f"VIN 长度应为17位，当前为 {len(vin_upper)} 位")
    if any(c in {"I", "O", "Q"} for c in vin_upper):
        raise HTTPException(400, "VIN 包含非法字符（不允许 I, O, Q）")

    result = decoder.decode(vin_upper)
    if result.get("error"):
        raise HTTPException(400, result["error"])
    if not result["valid"]:
        raise HTTPException(400, "VIN 解码失败")

    # 品牌映射
    raw_brand = result["brand"]
    mapped_brand = _map_vin_brand(raw_brand)

    if mapped_brand not in PARTS_DATABASE:
        raise HTTPException(404, f"VIN 识别品牌 '{raw_brand}' 不在配件库中")

    # 尝试匹配车型：先用 VDS model_code 模糊搜，再返回该品牌所有车型
    model_code = result["vds"].get("model_code", "").upper()
    matched_models = []
    for model_name in get_models(mapped_brand):
        # model_code 模糊匹配车型名
        if model_code and model_code.lower() in model_name.lower():
            matched_models.append(model_name)

    # 如果 VDS 没匹配上，返回品牌下所有车型
    if not matched_models:
        matched_models = get_models(mapped_brand)

    # 获取配件数据
    models_data = []
    for model_name in matched_models:
        model_data = PARTS_DATABASE[mapped_brand][model_name]
        models_data.append({
            "model": model_name,
            "years": model_data["years"],
            "engine": model_data["engine"],
            "parts": model_data["parts"],
        })

    return {
        "vin_info": {
            "vin": result["vin"],
            "brand": raw_brand,
            "mapped_brand": mapped_brand,
            "year": result["year"],
            "country": result["country"],
            "manufacturer": result["manufacturer"],
            "check_digit_valid": result["check_digit_valid"],
        },
        "total": len(models_data),
        "models": models_data,
    }
