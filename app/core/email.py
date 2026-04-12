"""
Email sending utility for ClayBag.
Uses SMTP (works with Gmail, AWS SES, any SMTP provider).
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    pdf_attachment: Optional[bytes] = None,
    attachment_filename: str = "order-confirmation.pdf",
) -> bool:
    """
    Send an HTML email with optional PDF attachment.
    Returns True on success, False on failure (never raises).
    """
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.warning("SMTP not configured — skipping email to %s", to_email)
        return False

    try:
        msg = MIMEMultipart("mixed")
        msg["From"] = f"ClayBag <{settings.SMTP_FROM or settings.SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Reply-To"] = settings.SMTP_FROM or settings.SMTP_USER

        # HTML body
        html_part = MIMEText(html_body, "html", "utf-8")
        msg.attach(html_part)

        # PDF attachment
        if pdf_attachment:
            pdf_part = MIMEApplication(pdf_attachment, _subtype="pdf")
            pdf_part.add_header(
                "Content-Disposition", "attachment", filename=attachment_filename
            )
            msg.attach(pdf_part)

        # Send
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            sender = settings.SMTP_FROM or settings.SMTP_USER
            server.sendmail(sender, [to_email], msg.as_string())

        logger.info("Email sent to %s: %s", to_email, subject)
        return True

    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, e)
        return False


def send_otp_email(to_email: str, otp: str) -> bool:
    """Send a password reset OTP email."""
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
    <body style="margin:0;padding:0;background:#f6f4ef;font-family:Helvetica,Arial,sans-serif;">
        <div style="max-width:600px;margin:0 auto;background:#ffffff;">
            <div style="background:#1b1b1b;padding:32px 24px;text-align:center;">
                <div style="font-size:28px;font-weight:bold;color:#ffffff;letter-spacing:2px;">
                    CLAY<span style="color:#fdc003;">BAG</span>
                </div>
                <div style="color:#888;font-size:11px;letter-spacing:3px;margin-top:4px;text-transform:uppercase;">
                    Small Batch. Big Brand.
                </div>
            </div>
            <div style="height:4px;background:#fdc003;"></div>
            <div style="padding:40px 24px;text-align:center;">
                <h1 style="font-size:22px;color:#1b1b1b;margin:0 0 12px 0;">Password Reset</h1>
                <p style="color:#666;font-size:14px;line-height:1.6;margin:0 0 32px 0;">
                    Use the code below to reset your password. This code expires in 10 minutes.
                </p>
                <div style="background:#f6f4ef;border:2px dashed #fdc003;border-radius:8px;padding:24px;margin-bottom:32px;">
                    <div style="font-size:36px;font-weight:bold;letter-spacing:12px;color:#1b1b1b;font-family:monospace;">
                        {otp}
                    </div>
                </div>
                <p style="color:#888;font-size:12px;line-height:1.6;">
                    If you didn't request this, you can safely ignore this email.
                </p>
            </div>
            <div style="background:#1b1b1b;padding:24px;text-align:center;">
                <div style="color:#888;font-size:12px;line-height:1.8;">
                    Need help? Email us at <a href="mailto:talk2us@claybag.com" style="color:#fdc003;">talk2us@claybag.com</a>
                </div>
                <div style="margin-top:16px;color:#555;font-size:10px;letter-spacing:2px;text-transform:uppercase;">
                    ClayBag &mdash; Building Brands Since 2024
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return send_email(to_email=to_email, subject="Password Reset OTP — ClayBag", html_body=html_body)


def send_order_confirmation(order, user, items_detail: list[dict]) -> bool:
    """
    Send order confirmation email with PDF attachment.
    Called after payment is confirmed.
    """
    from app.core.pdf_generator import generate_order_pdf

    order_num = order.order_number or f"CB-{order.id}"

    # Generate PDF
    try:
        pdf_bytes = generate_order_pdf(order, user, items_detail)
    except Exception as e:
        logger.error("PDF generation failed for order %s: %s", order_num, e)
        pdf_bytes = None

    # Build HTML email body
    items_html = ""
    for item in items_detail:
        label = item["product_name"]
        if item.get("variant_label"):
            label += f' <span style="color:#888;">({item["variant_label"]})</span>'
        items_html += f"""
        <tr>
            <td style="padding:12px 16px;border-bottom:1px solid #eee;font-size:14px;">{label}</td>
            <td style="padding:12px 16px;border-bottom:1px solid #eee;text-align:center;font-size:14px;">{item["quantity"]}</td>
            <td style="padding:12px 16px;border-bottom:1px solid #eee;text-align:right;font-size:14px;">&#8377;{item["total_price"]:,.2f}</td>
        </tr>"""

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
    <body style="margin:0;padding:0;background:#f6f4ef;font-family:Helvetica,Arial,sans-serif;">
        <div style="max-width:600px;margin:0 auto;background:#ffffff;">
            <!-- Header -->
            <div style="background:#1b1b1b;padding:32px 24px;text-align:center;">
                <div style="font-size:28px;font-weight:bold;color:#ffffff;letter-spacing:2px;">
                    CLAY<span style="color:#fdc003;">BAG</span>
                </div>
                <div style="color:#888;font-size:11px;letter-spacing:3px;margin-top:4px;text-transform:uppercase;">
                    Small Batch. Big Brand.
                </div>
            </div>

            <!-- Yellow accent stripe -->
            <div style="height:4px;background:#fdc003;"></div>

            <!-- Body -->
            <div style="padding:32px 24px;">
                <h1 style="font-size:24px;color:#1b1b1b;margin:0 0 8px 0;">
                    Thank you for your order!
                </h1>
                <p style="color:#666;font-size:14px;line-height:1.6;margin:0 0 24px 0;">
                    Hey {user.name.split(' ')[0]}, your order <strong>#{order_num}</strong> has been confirmed
                    and is now being processed. We're excited to help you build your brand!
                </p>

                <!-- Order summary card -->
                <div style="background:#f6f4ef;border-radius:8px;padding:20px;margin-bottom:24px;">
                    <div style="display:flex;justify-content:space-between;margin-bottom:12px;">
                        <div>
                            <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:2px;">Order Number</div>
                            <div style="font-size:18px;font-weight:bold;color:#1b1b1b;">#{order_num}</div>
                        </div>
                    </div>
                    <div style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:2px;margin-bottom:4px;">Shipping To</div>
                    <div style="font-size:14px;color:#1b1b1b;">
                        {order.shipping_name}<br/>
                        {order.shipping_address}<br/>
                        {order.shipping_city} {order.shipping_pincode}<br/>
                        {order.shipping_phone}
                    </div>
                </div>

                <!-- Items table -->
                <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">
                    <thead>
                        <tr style="background:#1b1b1b;">
                            <th style="padding:12px 16px;text-align:left;color:#fff;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Product</th>
                            <th style="padding:12px 16px;text-align:center;color:#fff;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Qty</th>
                            <th style="padding:12px 16px;text-align:right;color:#fff;font-size:12px;text-transform:uppercase;letter-spacing:1px;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>

                <!-- Totals -->
                <div style="border-top:3px solid #fdc003;padding-top:16px;">
                    <table style="width:100%;">
                        <tr>
                            <td style="font-size:14px;color:#888;padding:4px 0;">Subtotal</td>
                            <td style="text-align:right;font-size:14px;color:#1b1b1b;">&#8377;{order.total_amount:,.2f}</td>
                        </tr>
                        <tr>
                            <td style="font-size:14px;color:#888;padding:4px 0;">Shipping</td>
                            <td style="text-align:right;font-size:14px;color:#22c55e;font-weight:bold;">FREE</td>
                        </tr>
                        <tr>
                            <td style="font-size:18px;font-weight:bold;color:#1b1b1b;padding:12px 0 0 0;">Order Total</td>
                            <td style="text-align:right;font-size:18px;font-weight:bold;color:#1b1b1b;padding:12px 0 0 0;">&#8377;{order.total_amount:,.2f}</td>
                        </tr>
                    </table>
                </div>
            </div>

            <!-- CTA -->
            <div style="padding:0 24px 32px 24px;text-align:center;">
                <a href="https://claybag.com/orders/{order.id}"
                   style="display:inline-block;background:#fdc003;color:#1b1b1b;text-decoration:none;padding:14px 32px;font-weight:bold;font-size:13px;letter-spacing:2px;text-transform:uppercase;">
                    TRACK YOUR ORDER &rarr;
                </a>
            </div>

            <!-- Footer -->
            <div style="background:#1b1b1b;padding:24px;text-align:center;">
                <div style="color:#888;font-size:12px;line-height:1.8;">
                    Need help? Email us at <a href="mailto:talk2us@claybag.com" style="color:#fdc003;">talk2us@claybag.com</a><br/>
                    or call <a href="tel:+919886413339" style="color:#fdc003;">+91 98864 13339</a>
                </div>
                <div style="margin-top:16px;color:#555;font-size:10px;letter-spacing:2px;text-transform:uppercase;">
                    ClayBag &mdash; Building Brands Since 2024
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    subject = f"Order Confirmed! #{order_num} — ClayBag"
    attachment_name = f"ClayBag-Order-{order_num}.pdf"

    return send_email(
        to_email=user.email,
        subject=subject,
        html_body=html_body,
        pdf_attachment=pdf_bytes,
        attachment_filename=attachment_name,
    )
