"""
Generate a branded order confirmation / GST invoice PDF for ClayBag.
"""
import io
from datetime import datetime
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

from app.core.config import settings

# Register a Unicode-capable font for ₹ symbol
# Try DejaVu (commonly available on Linux/Docker), fallback to using HTML entity
_font_registered = False
for font_path in [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]:
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("UniFont", font_path))
        pdfmetrics.registerFont(TTFont("UniFont-Bold", font_path.replace("Sans.ttf", "Sans-Bold.ttf").replace("Regular", "Bold")))
        _font_registered = True
        break

RUPEE = "₹" if _font_registered else "Rs."
FONT_NAME = "UniFont" if _font_registered else "Helvetica"
FONT_NAME_BOLD = "UniFont-Bold" if _font_registered else "Helvetica-Bold"


YELLOW = colors.HexColor("#fdc003")
BLACK = colors.HexColor("#1b1b1b")
GRAY = colors.HexColor("#666666")
LIGHT_GRAY = colors.HexColor("#f4f2f0")


def generate_order_pdf(order, user, items_detail: List[dict]) -> bytes:
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
        fontName=FONT_NAME_BOLD,
        fontSize=22,
        textColor=BLACK,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "SectionHead",
        parent=styles["Heading3"],
        fontName=FONT_NAME_BOLD,
        fontSize=10,
        textColor=GRAY,
        spaceAfter=6,
        spaceBefore=14,
    ))
    styles.add(ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=9,
        textColor=BLACK,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName=FONT_NAME_BOLD,
        fontSize=9,
        textColor=BLACK,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        "CellHeader",
        parent=styles["Normal"],
        fontName=FONT_NAME_BOLD,
        fontSize=9,
        textColor=colors.white,
        leading=13,
    ))
    styles.add(ParagraphStyle(
        "SmallGray",
        parent=styles["Normal"],
        fontName=FONT_NAME,
        fontSize=8,
        textColor=GRAY,
        leading=11,
    ))
    styles.add(ParagraphStyle(
        "FooterText",
        parent=styles["Normal"],
        fontName=FONT_NAME,
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
            Paragraph(f"<b>Order Confirmation</b>", ParagraphStyle("", fontName=FONT_NAME_BOLD, fontSize=14, textColor=BLACK, alignment=TA_RIGHT)),
        ],
        [
            Paragraph("Premium Branded Merchandise", styles["SmallGray"]),
            "",
            Paragraph(f"Order #{order_num}<br/>Date: {order_date}", ParagraphStyle("", fontName=FONT_NAME, fontSize=9, textColor=GRAY, alignment=TA_RIGHT, leading=13)),
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
    gstin_line = f"GSTIN: {settings.COMPANY_GSTIN}<br/>" if settings.COMPANY_GSTIN else ""
    seller_info = f"""<b>Seller</b><br/>
{settings.COMPANY_LEGAL_NAME}<br/>
{settings.COMPANY_STATE}, India<br/>
{gstin_line}Email: talk2us@claybag.com"""

    state_line = f"State: {order.shipping_state}<br/>" if order.shipping_state else ""
    buyer_info = f"""<b>Buyer</b><br/>
{user.name}<br/>
{order.shipping_address}<br/>
{order.shipping_city} {order.shipping_pincode}<br/>
{state_line}{user.email}<br/>
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
        Paragraph("<b>#</b>", styles["CellHeader"]),
        Paragraph("<b>Product</b>", styles["CellHeader"]),
        Paragraph("<b>HSN</b>", styles["CellHeader"]),
        Paragraph("<b>Qty</b>", styles["CellHeader"]),
        Paragraph("<b>GST%</b>", styles["CellHeader"]),
        Paragraph("<b>Unit Price</b>", styles["CellHeader"]),
        Paragraph("<b>Total</b>", styles["CellHeader"]),
    ]
    item_rows = [item_header]

    for idx, item in enumerate(items_detail, 1):
        label = item["product_name"]
        if item.get("variant_label"):
            label += f' ({item["variant_label"]})'
        # Per-area item — append dimension breakdown to label so customer sees the full calculation
        is_area = item.get("computed_area") is not None and item.get("dimension_length") is not None
        if is_area:
            L = item.get("dimension_length") or 0
            B = item.get("dimension_breadth") or 0
            area = item.get("computed_area") or 0
            label += f'<br/><font size="7" color="#666666">{L}in &#215; {B}in &#215; {item["quantity"]} pcs = {area:.1f} sq.in</font>'
        gst_rate_disp = f'{item.get("gst_rate", 0):.0f}%' if item.get("gst_rate") else "-"
        # Qty column: number of stickers; Unit Price: per-sq-in rate for per-area, per-piece otherwise
        qty_disp = str(item["quantity"])
        unit_price_disp = f'{RUPEE}{item["unit_price"]:,.2f}'
        if is_area:
            unit_price_disp += '<br/><font size="6" color="#888888">/ sq.in</font>'
        item_rows.append([
            Paragraph(str(idx), styles["CellText"]),
            Paragraph(label, styles["CellText"]),
            Paragraph(item.get("hsn_code") or "-", styles["CellText"]),
            Paragraph(qty_disp, styles["CellText"]),
            Paragraph(gst_rate_disp, styles["CellText"]),
            Paragraph(unit_price_disp, styles["CellText"]),
            Paragraph(f'{RUPEE}{item["total_price"]:,.2f}', styles["CellText"]),
        ])

    items_table = Table(item_rows, colWidths=[20, 180, 50, 30, 40, 70, 80])
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
    total_label_style = ParagraphStyle("", fontName=FONT_NAME, fontSize=9, textColor=GRAY, alignment=TA_RIGHT)
    total_value_style = ParagraphStyle("", fontName=FONT_NAME, fontSize=9, textColor=GRAY, alignment=TA_RIGHT)
    total_bold_label = ParagraphStyle("", fontName=FONT_NAME_BOLD, fontSize=12, textColor=BLACK, alignment=TA_RIGHT)
    total_bold_value = ParagraphStyle("", fontName=FONT_NAME_BOLD, fontSize=12, textColor=BLACK, alignment=TA_RIGHT)

    totals_data = []
    # Show GST breakdown if computed
    if order.taxable_amount and order.taxable_amount > 0:
        totals_data.append([
            Paragraph("Taxable Amount", total_label_style),
            Paragraph(f"{RUPEE}{order.taxable_amount:,.2f}", total_value_style)
        ])
        if (order.cgst_amount or 0) > 0 or (order.sgst_amount or 0) > 0:
            totals_data.append([
                Paragraph("CGST", total_label_style),
                Paragraph(f"{RUPEE}{(order.cgst_amount or 0):,.2f}", total_value_style)
            ])
            totals_data.append([
                Paragraph("SGST", total_label_style),
                Paragraph(f"{RUPEE}{(order.sgst_amount or 0):,.2f}", total_value_style)
            ])
        if (order.igst_amount or 0) > 0:
            totals_data.append([
                Paragraph("IGST", total_label_style),
                Paragraph(f"{RUPEE}{(order.igst_amount or 0):,.2f}", total_value_style)
            ])

    totals_data.append([Paragraph("Shipping", total_label_style), Paragraph("FREE", total_value_style)])
    if (order.coins_applied or 0) > 0:
        totals_data.append([
            Paragraph("Clay Coins Applied", total_label_style),
            Paragraph(f"-{RUPEE}{order.coins_applied:,.2f}", total_value_style)
        ])
    if (order.referral_discount or 0) > 0:
        totals_data.append([
            Paragraph("Referral Discount (10%)", total_label_style),
            Paragraph(f"-{RUPEE}{order.referral_discount:,.2f}", total_value_style)
        ])
    totals_data.append(["", ""])
    totals_data.append([
        Paragraph("Order Total (Incl. GST)", total_bold_label),
        Paragraph(f"{RUPEE}{order.total_amount:,.2f}", total_bold_value)
    ])
    totals_table = Table(totals_data, colWidths=[380, 100])
    totals_table.setStyle(TableStyle([
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, YELLOW),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 4),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 10 * mm))

    # ── Footer ──────────────────────────────────────────────────
    elements.append(Paragraph(
        "Thank you for choosing ClayBag! Your order is being processed and will be shipped shortly.",
        ParagraphStyle("", fontName=FONT_NAME, fontSize=10, textColor=BLACK, alignment=TA_CENTER, spaceAfter=8),
    ))
    elements.append(Paragraph(
        "For support, reach out to us at talk2us@claybag.com or call +91 98864 13339",
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
