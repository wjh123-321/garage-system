"""Printing router — generate work-order print content for Bluetooth thermal printers."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models.work_order import WorkOrder

router = APIRouter(prefix="/api/printing", tags=["打印"])


def _build_print_html(wo: WorkOrder) -> str:
    """Build a receipt-style HTML page for thermal printers (80mm / 58mm)."""
    customer = wo.customer
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    date_str = now.strftime("%Y-%m-%d %H:%M")

    # ── header ──
    lines = [
        '<!DOCTYPE html>',
        '<html lang="zh-CN">',
        '<head>',
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '<title>工单打印</title>',
        '<style>',
        '* { margin: 0; padding: 0; box-sizing: border-box; }',
        'body {',
        '  font-family: "Courier New", "Noto Sans SC", monospace;',
        '  font-size: 13px;',
        '  width: 80mm;',
        '  padding: 4mm 3mm;',
        '  color: #000;',
        '  background: #fff;',
        '}',
        '.center { text-align: center; }',
        '.bold { font-weight: 700; }',
        '.divider { border-top: 1px dashed #333; margin: 4px 0; }',
        '.divider-solid { border-top: 1px solid #333; margin: 4px 0; }',
        'table { width: 100%; border-collapse: collapse; font-size: 12px; }',
        'th, td { padding: 2px 0; text-align: left; }',
        'th { border-bottom: 1px dashed #333; }',
        '.item-name { max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }',
        '.amount { text-align: right; }',
        '.info-grid { width: 100%; font-size: 12px; }',
        '.info-grid td { vertical-align: top; padding: 1px 0; }',
        '.footer { font-size: 11px; color: #555; }',
        '@media print {',
        '  @page { margin: 0; size: 80mm auto; }',
        '  body { margin: 0; padding: 2mm; }',
        '}',
        '</style>',
        '</head>',
        '<body>',
        '',
        f'<div class="center bold" style="font-size:16px;margin-bottom:2px;">{_shop_name()}</div>',
        f'<div class="center" style="font-size:11px;margin-bottom:4px;">工单打印 / {date_str}</div>',
        '<div class="divider-solid"></div>',
        '',
        # ── info block ──
        '<table class="info-grid">',
        f'<tr><td style="width:50px;">工单号</td><td class="bold">{wo.order_no}</td></tr>',
        f'<tr><td>状态</td><td>{_status_label(wo.status)}</td></tr>',
        f'<tr><td>车牌号</td><td class="bold">{wo.car_plate}</td></tr>',
        f'<tr><td>车型</td><td>{wo.car_model or "-"}</td></tr>',
        f'<tr><td>VIN</td><td style="font-size:11px;">{wo.vin or "-"}</td></tr>',
        f'<tr><td>里程</td><td>{_fmt_mileage(wo.mileage)}</td></tr>',
        '</table>',
        '<div class="divider"></div>',
        '',
        # ── customer ──
        '<table class="info-grid">',
        f'<tr><td style="width:50px;">客户</td><td>{customer.name if customer else "-"}</td></tr>',
        f'<tr><td>电话</td><td>{customer.phone if customer else "-"}</td></tr>',
        '</table>',
        '<div class="divider"></div>',
        '',
    ]

    # ── items table ──
    if wo.items:
        lines.append(
            '<table>'
            '<tr><th style="width:60%;">项目</th><th style="width:12%;text-align:right;">数量</th>'
            '<th style="width:14%;text-align:right;">单价</th><th style="width:14%;text-align:right;">小计</th></tr>'
        )
        for item in wo.items:
            lines.append(
                f'<tr>'
                f'<td class="item-name">{_escape_html(item.name)}</td>'
                f'<td class="amount">{item.quantity}</td>'
                f'<td class="amount">{item.unit_price:.2f}</td>'
                f'<td class="amount">{item.total_price:.2f}</td>'
                f'</tr>'
            )
        lines.append('</table>')
        lines.append('<div class="divider"></div>')

    # ── total ──
    lines.append(
        f'<table>'
        f'<tr><td style="font-size:14px;font-weight:700;">合计</td>'
        f'<td style="font-size:14px;font-weight:700;text-align:right;">¥ {wo.total_amount:.2f}</td></tr>'
        f'</table>'
    )
    lines.append('<div class="divider-solid"></div>')

    # ── description / remark / technician ──
    if wo.description:
        lines.append(f'<div style="font-size:12px;margin:2px 0;"><b>故障描述：</b>{_escape_html(wo.description)}</div>')
    if wo.remark:
        lines.append(f'<div style="font-size:12px;margin:2px 0;"><b>备注：</b>{_escape_html(wo.remark)}</div>')
    if wo.technician:
        lines.append(f'<div style="font-size:12px;margin:2px 0;"><b>维修技师：</b>{_escape_html(wo.technician)}</div>')

    lines.append('<div class="divider"></div>')

    # ── footer ──
    lines.append(
        '<div class="center footer">'
        '感谢您选择本店服务<br>'
        '本单据仅为维修凭证，不作为收款依据<br>'
        '打印时间: ' + date_str +
        '</div>'
    )

    if wo.completed_at:
        completed_local = wo.completed_at.astimezone()
        lines.append(
            f'<div class="center footer" style="margin-top:2px;">'
            f'完工时间: {completed_local.strftime("%Y-%m-%d %H:%M")}'
            f'</div>'
        )

    lines.append('</body></html>')
    return "\n".join(lines)


def _build_print_text(wo: WorkOrder) -> str:
    """Build a plain-text receipt for simple Bluetooth printers."""
    customer = wo.customer
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    date_str = now.strftime("%Y-%m-%d %H:%M")

    lines = [
        f"{'='*40}",
        f"  {_shop_name()}",
        f"  工单打印 / {date_str}",
        f"{'='*40}",
        f"",
        f"  工单号: {wo.order_no}",
        f"  状  态: {_status_label(wo.status)}",
        f"  车牌号: {wo.car_plate}",
        f"  车  型: {wo.car_model or '-'}",
        f"  VIN  : {wo.vin or '-'}",
        f"  里  程: {_fmt_mileage(wo.mileage)}",
        f"  客  户: {customer.name if customer else '-'}",
        f"  电  话: {customer.phone if customer else '-'}",
        f"{'-'*40}",
    ]

    if wo.items:
        lines.append(f"  {'项目':<20}{'数量':>6}{'单价':>8}{'小计':>8}")
        lines.append(f"  {'-'*42}")
        for item in wo.items:
            lines.append(
                f"  {item.name:<20}{item.quantity:>6}{item.unit_price:>8.2f}{item.total_price:>8.2f}"
            )
        lines.append(f"  {'-'*42}")

    lines.append(f"  合计: ¥ {wo.total_amount:.2f}")
    lines.append(f"{'='*40}")

    if wo.description:
        lines.extend(["", f"  故障描述: {wo.description}"])
    if wo.remark:
        lines.extend(["", f"  备  注: {wo.remark}"])
    if wo.technician:
        lines.extend(["", f"  维修技师: {wo.technician}"])

    lines.extend([
        "",
        f"{'='*40}",
        f"  感谢您选择本店服务",
        f"  本单据仅为维修凭证，不作为收款依据",
        f"  打印时间: {date_str}",
    ])

    if wo.completed_at:
        completed_local = wo.completed_at.astimezone()
        lines.append(f"  完工时间: {completed_local.strftime('%Y-%m-%d %H:%M')}")

    lines.append(f"{'='*40}")
    return "\r\n".join(lines)


# ── helpers ──


def _shop_name() -> str:
    """Return the shop name; could be pulled from settings in the future."""
    return "车库管理系统"


def _status_label(status: str) -> str:
    labels = {
        "pending": "待处理",
        "diagnosing": "诊断中",
        "in_progress": "维修中",
        "waiting_parts": "等配件",
        "completed": "已完成",
        "cancelled": "已取消",
    }
    return labels.get(status, status)


def _fmt_mileage(km: int) -> str:
    if km >= 100000:
        return f"{km / 10000:.1f}万公里"
    return f"{km} km"


def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ── endpoints ──


@router.post("/work-order/{order_id}")
def print_work_order(
    order_id: int,
    fmt: str = Query("html", alias="format", regex="^(html|text)$"),
    db: Session = Depends(get_db),
):
    """生成工单打印内容。

    返回格式化后的 HTML 或纯文本，前端可直接发送至蓝牙打印机。
    - `format=html`（默认）: 返回带样式的 HTML 页面，适合 80mm 热敏纸
    - `format=text` : 返回纯文本，适合简单指令打印机
    """
    wo = (
        db.query(WorkOrder)
        .options(joinedload(WorkOrder.customer), joinedload(WorkOrder.items))
        .filter(WorkOrder.id == order_id)
        .first()
    )
    if not wo:
        raise HTTPException(404, "工单不存在")

    if fmt == "text":
        content = _build_print_text(wo)
        return {
            "format": "text",
            "content": content,
            "content_type": "text/plain; charset=utf-8",
        }

    content = _build_print_html(wo)
    return {
        "format": "html",
        "content": content,
        "content_type": "text/html; charset=utf-8",
    }
