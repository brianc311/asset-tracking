import io

import barcode
import qrcode
from barcode.writer import ImageWriter
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.assets.models import Asset


def generate_qr_image(barcode_value: str, box_size: int = 10) -> io.BytesIO:
    qr = qrcode.QRCode(version=1, box_size=box_size, border=2)
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
        code_class = barcode.code128.Code128
        value = barcode_value

    code = code_class(value, writer=writer)
    buffer = io.BytesIO()
    code.write(buffer)
    buffer.seek(0)
    return buffer


def barcode_image_response(asset: Asset) -> HttpResponse:
    if asset.barcode_type == Asset.BarcodeType.QR:
        buffer = generate_qr_image(asset.barcode_value)
        content_type = "image/png"
    else:
        buffer = generate_1d_barcode_image(asset.barcode_value, asset.barcode_type)
        content_type = "image/png"

    response = HttpResponse(buffer.getvalue(), content_type=content_type)
    response["Content-Disposition"] = f'inline; filename="{asset.barcode_value}.png"'
    return response


def assets_pdf_bytes(assets, title: str = "Asset Report") -> bytes:
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

    data = [["#", "Barcode", "Site", "Product", "Serial", "Model", "Location", "Comments"]]
    for asset in assets:
        data.append([
            str(asset.asset_number or "—"),
            asset.barcode_value,
            asset.site_name[:20] or "—",
            asset.product_name[:30],
            asset.serial_number[:20] or "—",
            asset.model_number[:20] or "—",
            asset.location[:20] or "—",
            (asset.comments[:40] + "…") if len(asset.comments) > 40 else (asset.comments or "—"),
        ])

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
    elements.append(Paragraph(f"Total items: {len(assets)}", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def assets_pdf_response(assets, title: str = "Asset Report") -> HttpResponse:
    response = HttpResponse(assets_pdf_bytes(assets, title=title), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{title.replace(" ", "_").lower()}.pdf"'
    return response
