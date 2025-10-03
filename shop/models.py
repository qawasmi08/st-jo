from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Customer(TimeStampedModel):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - simple display
        return f"{self.name} ({self.phone})"


class Category(TimeStampedModel):
    name_ar = models.CharField(max_length=255, unique=True)
    parent = models.ForeignKey(
        "self", related_name="children", on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name_ar"]

    def __str__(self) -> str:  # pragma: no cover - simple display
        return self.name_ar


class Brand(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:  # pragma: no cover - simple display
        return self.name


class Product(TimeStampedModel):
    name_ar = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    images = models.JSONField(default=list, blank=True)
    specs = models.JSONField(blank=True, null=True)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.PROTECT)
    brand = models.ForeignKey(Brand, related_name="products", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["name_ar"]

    def __str__(self) -> str:  # pragma: no cover - simple display
        return f"{self.name_ar} ({self.sku})"


class StandardOrderStatus(models.TextChoices):
    NEW = "new", _("جديد")
    CONFIRMED = "confirmed", _("مؤكد")
    READY = "ready_for_pickup", _("جاهز للاستلام")
    COMPLETED = "completed", _("مكتمل")
    CANCELLED = "cancelled", _("ملغى")


class StandardOrder(TimeStampedModel):
    customer = models.ForeignKey(Customer, related_name="standard_orders", on_delete=models.CASCADE)
    status = models.CharField(max_length=32, choices=StandardOrderStatus.choices, default=StandardOrderStatus.NEW)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="JOD")
    pickup_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"Order #{self.pk}"

    @transaction.atomic
    def confirm(self) -> None:
        if self.status != StandardOrderStatus.NEW:
            raise ValidationError("لا يمكن تأكيد الطلب في هذه الحالة.")
        self._ensure_stock()
        self._apply_stock_deduction()
        self.status = StandardOrderStatus.CONFIRMED
        self.save(update_fields=["status"])

    def mark_ready(self) -> None:
        if self.status != StandardOrderStatus.CONFIRMED:
            raise ValidationError("لا يمكن جعل الطلب جاهزاً إلا بعد التأكيد.")
        self.status = StandardOrderStatus.READY
        self.save(update_fields=["status"])

    def complete(self) -> None:
        if self.status not in {StandardOrderStatus.READY, StandardOrderStatus.CONFIRMED}:
            raise ValidationError("لا يمكن إكمال الطلب في هذه الحالة.")
        self.status = StandardOrderStatus.COMPLETED
        self.save(update_fields=["status"])

    def cancel(self) -> None:
        if self.status == StandardOrderStatus.CANCELLED:
            return
        if self.status in {StandardOrderStatus.CONFIRMED, StandardOrderStatus.READY}:
            self._restore_stock()
        self.status = StandardOrderStatus.CANCELLED
        self.save(update_fields=["status"])

    def _ensure_stock(self) -> None:
        for item in self.items.select_related("product"):
            if item.product.stock < item.qty:
                raise ValidationError(f"المخزون غير كافٍ للمنتج {item.product.sku}.")

    def _apply_stock_deduction(self) -> None:
        for item in self.items.select_related("product").select_for_update():
            product = item.product
            if product.stock < item.qty:
                raise ValidationError(f"المخزون غير كافٍ للمنتج {product.sku}.")
            product.stock -= item.qty
            product.save(update_fields=["stock"])

    def _restore_stock(self) -> None:
        for item in self.items.select_related("product").select_for_update():
            product = item.product
            product.stock += item.qty
            product.save(update_fields=["stock"])

    def recalculate_total(self) -> None:
        total = sum(item.total_price for item in self.items.all())
        self.total = total
        self.save(update_fields=["total"])


class StandardOrderItem(models.Model):
    order = models.ForeignKey(StandardOrder, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="order_items", on_delete=models.PROTECT)
    qty = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("order", "product")

    @property
    def total_price(self) -> Decimal:
        return self.unit_price * self.qty

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.product} x {self.qty}"


class CustomOrderStatus(models.TextChoices):
    NEW = "new", _("طلب جديد")
    SURVEY_SCHEDULED = "site_survey_scheduled", _("تم جدولة الزيارة")
    SURVEYED = "surveyed", _("تمت المعاينة")
    QUOTE_SENT = "quote_sent", _("تم إرسال العرض")
    APPROVED = "approved", _("تمت الموافقة")
    SCHEDULED_INSTALL = "scheduled_install", _("تمت جدولة التركيب")
    INSTALLED = "installed", _("تم التركيب")
    HANDED_OVER = "handed_over", _("تم التسليم")
    COMPLETED = "completed", _("مكتمل")
    CANCELLED = "cancelled", _("ملغى")


class CustomOrder(TimeStampedModel):
    customer = models.ForeignKey(Customer, related_name="custom_orders", on_delete=models.CASCADE)
    status = models.CharField(max_length=32, choices=CustomOrderStatus.choices, default=CustomOrderStatus.NEW)
    requirement_summary = models.TextField()
    site_address = models.CharField(max_length=255, blank=True)
    site_city = models.CharField(max_length=120, blank=True)
    site_geo_lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    site_geo_lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    preferred_contact_time = models.CharField(max_length=120, blank=True)
    attachments = models.JSONField(default=list, blank=True)
    quote_subtotal = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    quote_discount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    quote_total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    currency = models.CharField(max_length=8, default="JOD")
    quote_pdf_url = models.URLField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover
        return f"CustomOrder #{self.pk}"

    def clean(self) -> None:
        if self.quote_subtotal is not None and self.quote_discount is not None:
            if self.quote_discount > self.quote_subtotal:
                raise ValidationError("لا يمكن أن يتجاوز الخصم قيمة المجموع الفرعي.")
        if self.quote_total is not None and self.quote_subtotal is not None and self.quote_discount is not None:
            if self.quote_total != self.quote_subtotal - self.quote_discount:
                raise ValidationError("إجمالي العرض لا يتطابق مع المجموع الفرعي ناقص الخصم.")

    def require_lines_for_quote(self) -> None:
        if not self.lines.exists():
            raise ValidationError("يجب إضافة بنود قبل إرسال العرض.")

    def set_status(self, new_status: str, allowed_previous: Iterable[str]) -> None:
        if self.status not in allowed_previous:
            raise ValidationError("الانتقال للحالة المطلوبة غير مسموح.")
        self.status = new_status
        self.save(update_fields=["status"])


class CustomOrderLine(models.Model):
    class ItemType(models.TextChoices):
        PRODUCT = "product", _("منتج")
        SERVICE = "service", _("خدمة")

    custom_order = models.ForeignKey(CustomOrder, related_name="lines", on_delete=models.CASCADE)
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, blank=True)
    qty = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ["id"]

    @property
    def total_price(self) -> Decimal:
        if self.unit_price is None:
            return Decimal("0.00")
        return self.qty * self.unit_price

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.item_type})"
