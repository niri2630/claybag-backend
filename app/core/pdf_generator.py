"""
Generate a branded order confirmation PDF — matches the format from the
existing Logosouk invoice but branded for ClayBag, without the Invoice No. field.
"""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER


YELLOW = colors.HexColor("#fdc003")
BLACK = colors.HexColor("#1b1b1b")
GRAY = colors.HexColor("#666666")
LIGHT_GRAY = colors.HexColor("#f4f2f0")


def generate_order_pdf(order, user, items_detail: list[dict]) -> bytes:
    """
    Generate a PDF order confirmation and return it as bytes.

    Parameters
    ----------
    order : Order model instance
    user  : User model instance (the buyer)
    items_detail : list of dicts with keys:
        product_name, variant_label, quantity, unit_price, total_price
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    styles.add(ParagraphStyle(
        "BrandTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=BLACK,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "SectionHead",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=GRAY,
        spaceAfter=6,
        spaceBefore=14,
    ))
    styles.add(ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=BLACK,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=BLACK,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        "SmallGray",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=GRAY,
        leading=11,
    ))
    styles.add(ParagraphStyle(
        "FooterText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        textColor=GRAY,
        alignment=TA_CENTER,
    ))

    elements: list = []

    # ── Header ──────────────────────────────────────────────────
    order_date = order.created_at.strftime("%B %d, %Y") if order.created_at else datetime.utcnow().strftime("%B %d, %Y")
    order_num = order.order_number or f"CB-{order.id}"

    header_data = [
        [
            Paragraph("CLAY<font color='#fdc003'>BAG</font>", styles["BrandTitle"]),
            "",
            Paragraph(f"<b>Order Confirmation</b>", ParagraphStyle("", fontName="Helvetica-Bold", fontSize=14, textColor=BLACK, alignment=TA_RIGHT)),
        ],
        [
            Paragraph("Premium Branded Merchandise", styles["SmallGray"]),
            "",
            Paragraph(f"Order #{order_num}<br/>Date: {order_date}", ParagraphStyle("", fontName="Helvetica", fontSize=9, textColor=GRAY, alignment=TA_RIGHT, leading=13)),
        ],
    ]
    header_table = Table(header_data, colWidths=[200, 100, 200])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 4 * mm))

    # Yellow divider line
    divider_data = [["", ""]]
    divider = Table(divider_data, colWidths=[500, 0])
    divider.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (0, 0), 2, YELLOW),
    ]))
    elements.append(divider)
    elements.append(Spacer(1, 6 * mm))

    # ── Seller / Buyer side by side ─────────────────────────────
    seller_info = """<b>Seller</b><br/>
Logosouk Merces Private Limited<br/>
543, 32nd Cross, 9th Main,<br/>
4th Block, Jayanagar,<br/>
Bangalore - 560 011<br/>
GSTN: 29AADCL6003E2ZS<br/>
CIN: U74999KA2018PTC112752"""

    buyer_info = f"""<b>Buyer</b><br/>
{user.name}<br/>
{order.shipping_address}<br/>
{order.shipping_city} {order.shipping_pincode}<br/>
{user.email}<br/>
{order.shipping_phone}"""

    addr_data = [
        [
            Paragraph(seller_info, styles["CellText"]),
            Paragraph(buyer_info, styles["CellText"]),
        ]
    ]
    addr_table = Table(addr_data, colWidths=[250, 250])
    addr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elements.append(addr_table)
    elements.append(Spacer(1, 6 * mm))

    # ── Shipping Address ────────────────────────────────────────
    elements.append(Paragraph("Shipping Address", styles["SectionHead"]))
    ship_text = f"""{order.shipping_name}<br/>
{order.shipping_address}<br/>
{order.shipping_city} {order.shipping_pincode}<br/>
{order.shipping_phone}"""
    if order.notes:
        ship_text += f"<br/><br/><i>Note: {order.notes}</i>"
    elements.append(Paragraph(ship_text, styles["CellText"]))
    elements.append(Spacer(1, 6 * mm))

    # ── Items Table ─────────────────────────────────────────────
    elements.append(Paragraph("Order Items", styles["SectionHead"]))

    item_header = [
        Paragraph("<b>#</b>", styles["CellBold"]),
        Paragraph("<b>Product</b>", styles["CellBold"]),
        Paragraph("<b>Qty</b>", styles["CellBold"]),
        Paragraph("<b>Unit Price</b>", styles["CellBold"]),
        Paragraph("<b>Total</b>", styles["CellBold"]),
    ]
    item_rows = [item_header]

    for idx, item in enumerate(items_detail, 1):
        label = item["product_name"]
        if item.get("variant_label"):
            label += f' ({item["variant_label"]})'
        item_rows.append([
            Paragraph(str(idx), styles["CellText"]),
            Paragraph(label, styles["CellText"]),
            Paragraph(str(item["quantity"]), styles["CellText"]),
            Paragraph(f'₹{item["unit_price"]:,.2f}', styles["CellText"]),
            Paragraph(f'₹{item["total_price"]:,.2f}', styles["CellText"]),
        ])

    items_table = Table(item_rows, colWidths=[30, 250, 40, 80, 80])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLACK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 6 * mm))

    # ── Totals ──────────────────────────────────────────────────
    totals_data = [
        ["Subtotal", f"₹{order.total_amount:,.2f}"],
        ["Shipping", "FREE"],
        ["", ""],
        ["Order Total", f"₹{order.total_amount:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[380, 100])
    totals_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), GRAY),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, -1), (-1, -1), 12),
        ("TEXTCOLOR", (0, -1), (-1, -1), BLACK),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, YELLOW),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 10 * mm))

    # ── Footer ──────────────────────────────────────────────────
    elements.append(Paragraph(
        "Thank you for choosing ClayBag! Your order is being processed and will be shipped shortly.",
        ParagraphStyle("", fontName="Helvetica", fontSize=10, textColor=BLACK, alignment=TA_CENTER, spaceAfter=8),
    ))
    elements.append(Paragraph(
        "For support, reach out to us at support@claybag.com or call +91 98864 13339",
        styles["FooterText"],
    ))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(
        "ClayBag — Small Batch. Big Brand. | claybag.com",
        styles["FooterText"],
    ))

    doc.build(elements)
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes
