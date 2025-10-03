from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from .models import (
    Brand,
    Category,
    CustomOrder,
    CustomOrderLine,
    StandardOrder,
    StandardOrderItem,
)
from .services import generate_custom_order_quote_pdf


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name_ar", "parent", "created_at")
    search_fields = ("name_ar",)
    list_filter = ("parent",)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


class StandardOrderItemInline(admin.TabularInline):
    model = StandardOrderItem
    extra = 0
    readonly_fields = ("product", "qty", "unit_price")


@admin.register(StandardOrder)
class StandardOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "total", "created_at")
    list_filter = ("status", "customer__city", "created_at")
    search_fields = ("customer__name", "customer__phone")
    inlines = [StandardOrderItemInline]
    actions = ["action_confirm", "action_ready", "action_complete"]

    def action_confirm(self, request, queryset):
        for order in queryset:
            try:
                order.confirm()
            except Exception as exc:  # pylint: disable=broad-except
                self.message_user(request, f"تعذر تأكيد الطلب {order.pk}: {exc}", level=messages.ERROR)
        self.message_user(request, _("تم تحديث الحالات"), level=messages.SUCCESS)

    action_confirm.short_description = "تأكيد الطلبات"  # type: ignore[attr-defined]

    def action_ready(self, request, queryset):
        for order in queryset:
            try:
                order.mark_ready()
            except Exception as exc:  # pylint: disable=broad-except
                self.message_user(request, f"تعذر تحديث الطلب {order.pk}: {exc}", level=messages.ERROR)
        self.message_user(request, _("تم تحديث الحالات"), level=messages.SUCCESS)

    action_ready.short_description = "جاهز للاستلام"  # type: ignore[attr-defined]

    def action_complete(self, request, queryset):
        for order in queryset:
            try:
                order.complete()
            except Exception as exc:  # pylint: disable=broad-except
                self.message_user(request, f"تعذر إكمال الطلب {order.pk}: {exc}", level=messages.ERROR)
        self.message_user(request, _("تم تحديث الحالات"), level=messages.SUCCESS)

    action_complete.short_description = "تم التسليم"  # type: ignore[attr-defined]


class CustomOrderLineInline(admin.TabularInline):
    model = CustomOrderLine
    extra = 0


@admin.register(CustomOrder)
class CustomOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "status", "quote_total", "created_at")
    list_filter = ("status", "customer__city", "created_at")
    search_fields = ("customer__name", "customer__phone")
    inlines = [CustomOrderLineInline]
    actions = ["action_generate_pdf", "action_approve", "action_schedule_install"]

    def action_generate_pdf(self, request, queryset):
        for order in queryset:
            try:
                order.require_lines_for_quote()
                generate_custom_order_quote_pdf(order)
            except Exception as exc:  # pylint: disable=broad-except
                self.message_user(request, f"تعذر توليد العرض للطلب {order.pk}: {exc}", level=messages.ERROR)
        self.message_user(request, _("تم توليد ملفات PDF"), level=messages.SUCCESS)

    action_generate_pdf.short_description = "توليد PDF العرض"  # type: ignore[attr-defined]

    def action_approve(self, request, queryset):
        for order in queryset:
            try:
                order.set_status(CustomOrderStatus.APPROVED, [CustomOrderStatus.QUOTE_SENT])
            except Exception as exc:  # pylint: disable=broad-except
                self.message_user(request, f"تعذر الموافقة على الطلب {order.pk}: {exc}", level=messages.ERROR)
        self.message_user(request, _("تم تحديث الحالات"), level=messages.SUCCESS)

    action_approve.short_description = "اعتماد العرض"  # type: ignore[attr-defined]

    def action_schedule_install(self, request, queryset):
        for order in queryset:
            try:
                order.set_status(CustomOrderStatus.SCHEDULED_INSTALL, [CustomOrderStatus.APPROVED])
            except Exception as exc:  # pylint: disable=broad-except
                self.message_user(request, f"تعذر جدولة التركيب للطلب {order.pk}: {exc}", level=messages.ERROR)
        self.message_user(request, _("تم تحديث الحالات"), level=messages.SUCCESS)

    action_schedule_install.short_description = "جدولة التركيب"  # type: ignore[attr-defined]
