import base64
import io

import barcode
import qrcode
from barcode.writer import ImageWriter
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.assets.models import Asset
from apps.assets.report_columns import (
    REPORT_COLUMN_LABELS,
    parse_report_columns,
    report_column_cells,
    visible_report_columns,
)


def generate_qr_image(barcode_value: str, box_size: int = 10) -> io.BytesIO:
    qr = qrcode.QRCode(version=None, box_size=box_size, border=2)
    qr.add_data(barcode_value)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generate_1d_barcode_image(barcode_value: str, barcode_type: str = "code128") -> io.BytesIO:
    writer = ImageWriter()
    if barcode_type == "code39":
        code_class = barcode.codex.Code39
        value = barcode_value
    elif barcode_type == "ean13":
        code_class = barcode.ean.EuropeanArticleNumber13
        value = barcode_value.zfill(12)[:12]
    else:
        code_class = barcode.Code128
        value = barcode_value

    code = code_class(value, writer=writer)
    buffer = io.BytesIO()
    code.write(buffer)
    buffer.seek(0)
    return buffer


def barcode_png_for_value(value: str) -> bytes:
    return generate_1d_barcode_image(value, "code128").getvalue()


def barcode_data_uri(value: str) -> str:
    try:
        png = barcode_png_for_value(value)
        return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    except Exception:
        return ""


def asset_details_qr_text(asset: Asset) -> str:
    lines = []
    device_name = (asset.device_name or "").strip()
    location = (asset.location or "").strip()
    serial = (asset.serial_number or "").strip()
    mac = (asset.mac_address or "").strip()
    mac_2 = (asset.mac_address_2 or "").strip()
    if device_name:
        lines.append(f"Device Name: {device_name}")
    if location:
        lines.append(f"Location: {location}")
    if serial:
        lines.append(f"Serial: {serial}")
    if mac:
        lines.append(f"MAC: {mac}")
    if mac_2:
        lines.append(f"MAC 2: {mac_2}")
    if not lines:
        return "No device name, location, serial, or MAC"
    return "\n".join(lines)


def barcode_image_response(
    asset: Asset,
    *,
    data: str | None = None,
    as_qr: bool = False,
    filename_suffix: str | None = None,
) -> HttpResponse:
    payload = asset.barcode_value if data is None else data
    if as_qr or asset.barcode_type == Asset.BarcodeType.QR:
        buffer = generate_qr_image(payload)
    else:
        buffer = generate_1d_barcode_image(payload, asset.barcode_type)

    suffix = f"-{filename_suffix}" if filename_suffix else ""
    filename = f"{asset.barcode_value}{suffix}.png"
    response = HttpResponse(buffer.getvalue(), content_type="image/png")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def assets_have_second_mac(assets) -> bool:
    if hasattr(assets, "exclude"):
        return assets.exclude(mac_address_2="").exists()
    return any((getattr(asset, "mac_address_2", None) or "").strip() for asset in assets)


def asset_report_table_data(assets, column_keys=None):
    show_mac_2 = assets_have_second_mac(assets)
    keys = visible_report_columns(column_keys or parse_report_columns(None), show_mac_2=show_mac_2)
    data = [[REPORT_COLUMN_LABELS[key] for key in keys]]
    for asset in assets:
        cells = report_column_cells(asset, show_mac_2=show_mac_2)
        data.append([cells[key] for key in keys])
    return data, show_mac_2


def assets_pdf_bytes(assets, title: str = "Asset Report", column_keys=None) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#6366f1"),
    )

    elements = [Paragraph(title, title_style), Spacer(1, 0.2 * inch)]
    data, _show_mac_2 = asset_report_table_data(assets, column_keys=column_keys)

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    elements.append(table)
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph(f"Total items: {max(len(data) - 1, 0)}", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def assets_pdf_response(assets, title: str = "Asset Report", column_keys=None) -> HttpResponse:
    response = HttpResponse(
        assets_pdf_bytes(assets, title=title, column_keys=column_keys),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = f'attachment; filename="{title.replace(" ", "_").lower()}.pdf"'
    return response


def batch_report_pdf_response(assets, *, site_name: str, product_name: str) -> HttpResponse:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.35 * inch,
        rightMargin=0.35 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"Batch Report — {site_name} — {product_name}", styles["Heading1"]),
        Spacer(1, 0.2 * inch),
    ]
    show_mac_2 = assets_have_second_mac(assets)
    headers = ["Site", "Type", "Serial", "MAC"]
    if show_mac_2:
        headers.append("MAC 2")
    headers.append("Timestamp")
    data = [headers]
    for asset in assets:
        created_at = timezone.localtime(asset.created_at).strftime("%Y-%m-%d %H:%M:%S")
        row = [
            asset.site_name or "—",
            asset.product_name or "—",
            asset.serial_number or "—",
            asset.mac_address or "—",
        ]
        if show_mac_2:
            row.append(asset.mac_address_2 or "—")
        row.append(created_at)
        data.append(row)

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.extend([table, Spacer(1, 0.3 * inch), Paragraph(f"Total items: {len(data) - 1}", styles["Normal"])])
    doc.build(elements)

    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="batch_report.pdf"'
    return response
