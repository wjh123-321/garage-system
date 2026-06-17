"""VIN识别 API router."""

from fastapi import APIRouter, HTTPException, Query

from ..services.vin_service import VinDecoder, _WMI_TABLE

router = APIRouter(prefix="/api/vin", tags=["VIN识别"])

decoder = VinDecoder()

# 非法字符（VIN 不允许 I, O, Q）
_FORBIDDEN_CHARS = {"I", "O", "Q"}


@router.get("/decode/{vin}")
def decode_vin(vin: str):
    """解码 VIN 车架号。

    校验规则：
    - 长度必须为 17 位
    - 不允许包含 I, O, Q 字符
    """
    vin_upper = vin.strip().upper()

    # 长度校验
    if len(vin_upper) != 17:
        raise HTTPException(400, f"VIN 长度应为17位，当前为 {len(vin_upper)} 位")

    # 非法字符校验
    if any(c in _FORBIDDEN_CHARS for c in vin_upper):
        raise HTTPException(400, "VIN 包含非法字符（不允许 I, O, Q）")

    result = decoder.decode(vin_upper)

    if result.get("error"):
        raise HTTPException(400, result["error"])

    return {
        "vin": result["vin"],
        "wmi": result["wmi"],
        "vds": result["vds"],
        "vis": result["vis"],
        "manufacturer": result["manufacturer"],
        "brand": result["brand"],
        "year": result["year"],
        "country": result["country"],
        "full_name": result["full_name"],
        "valid": result["valid"],
        "check_digit_valid": result["check_digit_valid"],
    }


@router.get("/brands")
def list_brands(country: str = Query("", description="按国家筛选，如：中国、德国、日本")):
    """返回支持的品牌列表，可选按国家筛选。"""
    seen: set = set()
    brands: list[dict] = []

    for _wmi, (_manufacturer, brand, c) in _WMI_TABLE.items():
        if country and c != country:
            continue
        key = (brand, c)
        if key not in seen:
            seen.add(key)
            brands.append({
                "brand": brand,
                "country": c,
            })

    brands.sort(key=lambda x: (x["country"], x["brand"]))
    return {"total": len(brands), "items": brands}
