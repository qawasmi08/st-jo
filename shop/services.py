from __future__ import annotations

import base64
import io
from decimal import Decimal

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.template.loader import render_to_string
from weasyprint import HTML

from .models import CustomOrder


def generate_custom_order_quote_pdf(custom_order: CustomOrder) -> str:
    subtotal = custom_order.quote_subtotal or Decimal("0.00")
    discount = custom_order.quote_discount or Decimal("0.00")
    total = custom_order.quote_total or (subtotal - discount)

    file_name = f"{settings.PDF_STORAGE_FOLDER}/custom-order-{custom_order.pk}.pdf"
    url = default_storage.url(file_name)

    qr_buffer = io.BytesIO()
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color=settings.STORE_INFO["theme_colors"]["primary"], back_color="white")
    img.save(qr_buffer, format="PNG")
    qr_image_base64 = base64.b64encode(qr_buffer.getvalue()).decode("utf-8")

    context = {
        "order": custom_order,
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "store": settings.STORE_INFO,
        "qr_image_base64": qr_image_base64,
    }

    html_string = render_to_string("quotes/custom_order.html", context)
    pdf_file = HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf(stylesheets=None)
    if default_storage.exists(file_name):
        default_storage.delete(file_name)
    saved_path = default_storage.save(file_name, ContentFile(pdf_file))
    url = default_storage.url(saved_path)
    custom_order.quote_pdf_url = url
    custom_order.save(update_fields=["quote_pdf_url"])
    return url
