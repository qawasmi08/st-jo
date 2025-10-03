from __future__ import annotations

from decimal import Decimal
from typing import List

from django.db import transaction
from rest_framework import serializers

from .models import (
    Brand,
    Category,
    CustomOrder,
    CustomOrderLine,
    CustomOrderStatus,
    Customer,
    Product,
    StandardOrder,
    StandardOrderItem,
    StandardOrderStatus,
)
from .utils import normalize_jordan_phone


class CustomerSerializer(serializers.ModelSerializer):
    phone = serializers.CharField()
    whatsapp = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "phone",
            "whatsapp",
            "email",
            "address",
            "city",
            "notes",
        ]

    def validate_phone(self, value: str) -> str:
        return normalize_jordan_phone(value)

    def validate_whatsapp(self, value: str) -> str:
        if value:
            return normalize_jordan_phone(value)
        return value

    def create(self, validated_data):
        phone = validated_data["phone"]
        customer, _ = Customer.objects.update_or_create(
            phone=phone,
            defaults=validated_data,
        )
        return customer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name_ar", "parent"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name"]


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    brand = serializers.PrimaryKeyRelatedField(queryset=Brand.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Product
        fields = [
            "id",
            "name_ar",
            "sku",
            "price",
            "stock",
            "is_active",
            "images",
            "specs",
            "category",
            "brand",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class StandardOrderItemInputSerializer(serializers.Serializer):
    sku = serializers.CharField()
    qty = serializers.IntegerField(min_value=1)


class StandardOrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = StandardOrderItem
        fields = ["id", "product", "qty", "unit_price", "total_price"]
        read_only_fields = ["total_price"]


class StandardOrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer()
    items = StandardOrderItemInputSerializer(many=True, write_only=True)

    class Meta:
        model = StandardOrder
        fields = [
            "id",
            "customer",
            "status",
            "total",
            "currency",
            "pickup_notes",
            "created_at",
            "items",
        ]
        read_only_fields = ["status", "total", "currency", "created_at"]

    def validate(self, attrs):
        items = attrs.get("items")
        if self.instance is None and not items:
            raise serializers.ValidationError("يجب إضافة عناصر للطلب")
        return super().validate(attrs)

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        if not items_data:
            raise serializers.ValidationError({"items": "يجب إضافة عناصر للطلب"})
        customer_data = validated_data.pop("customer")
        customer_serializer = CustomerSerializer(data=customer_data)
        customer_serializer.is_valid(raise_exception=True)
        customer = customer_serializer.save()

        with transaction.atomic():
            order = StandardOrder.objects.create(customer=customer, pickup_notes=validated_data.get("pickup_notes", ""))
            total = Decimal("0.00")
            seen_skus = set()
            for item in items_data:
                sku = item.get("sku")
                if sku in seen_skus:
                    raise serializers.ValidationError({"items": f"تم تكرار المنتج {sku}"})
                seen_skus.add(sku)
                qty = int(item.get("qty", 0))
                try:
                    product = Product.objects.get(sku=sku, is_active=True)
                except Product.DoesNotExist as exc:
                    raise serializers.ValidationError({"items": f"المنتج برقم {sku} غير موجود"}) from exc
                if product.stock < qty:
                    raise serializers.ValidationError({"items": f"المخزون غير كافٍ للمنتج {sku}"})
                order_item = StandardOrderItem.objects.create(
                    order=order,
                    product=product,
                    qty=qty,
                    unit_price=product.price,
                )
                total += order_item.total_price
            order.total = total
            order.save(update_fields=["total"])
        return order

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["items"] = StandardOrderItemSerializer(instance.items.all(), many=True).data
        return data


class StandardOrderStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=StandardOrderStatus.choices)


class CustomOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomOrderLine
        fields = ["id", "item_type", "name", "sku", "qty", "unit_price", "total_price"]
        read_only_fields = ["id", "total_price"]


class CustomOrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer()
    lines = CustomOrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = CustomOrder
        fields = [
            "id",
            "customer",
            "status",
            "requirement_summary",
            "site_address",
            "site_city",
            "site_geo_lat",
            "site_geo_lng",
            "preferred_contact_time",
            "attachments",
            "quote_subtotal",
            "quote_discount",
            "quote_total",
            "currency",
            "quote_pdf_url",
            "created_at",
            "updated_at",
            "lines",
        ]
        read_only_fields = [
            "status",
            "quote_subtotal",
            "quote_discount",
            "quote_total",
            "currency",
            "quote_pdf_url",
            "created_at",
            "updated_at",
            "lines",
        ]

    def create(self, validated_data):
        customer_data = validated_data.pop("customer")
        customer_serializer = CustomerSerializer(data=customer_data)
        customer_serializer.is_valid(raise_exception=True)
        customer = customer_serializer.save()
        custom_order = CustomOrder.objects.create(customer=customer, **validated_data)
        return custom_order


class CustomOrderLinesBulkSerializer(serializers.Serializer):
    lines = CustomOrderLineSerializer(many=True)
    quote_discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    def validate_lines(self, value: List[dict]) -> List[dict]:
        if not value:
            raise serializers.ValidationError("يجب إضافة بند واحد على الأقل")
        return value

    def save(self, custom_order: CustomOrder) -> CustomOrder:
        lines_data = self.validated_data["lines"]
        discount = self.validated_data.get("quote_discount", Decimal("0.00"))
        subtotal = Decimal("0.00")
        with transaction.atomic():
            custom_order.lines.all().delete()
            bulk_lines = []
            for line in lines_data:
                unit_price = line.get("unit_price")
                qty = Decimal(str(line.get("qty")))
                if unit_price is not None:
                    subtotal += qty * Decimal(str(unit_price))
                bulk_lines.append(
                    CustomOrderLine(
                        custom_order=custom_order,
                        item_type=line["item_type"],
                        name=line["name"],
                        sku=line.get("sku", ""),
                        qty=qty,
                        unit_price=line.get("unit_price"),
                    )
                )
            CustomOrderLine.objects.bulk_create(bulk_lines)
            if discount > subtotal:
                raise serializers.ValidationError("لا يمكن أن يتجاوز الخصم قيمة المجموع الفرعي")
            custom_order.quote_subtotal = subtotal
            custom_order.quote_discount = discount
            custom_order.quote_total = subtotal - discount
            custom_order.quote_pdf_url = ""
            custom_order.status = CustomOrderStatus.QUOTE_SENT
            custom_order.full_clean()
            custom_order.save(update_fields=["quote_subtotal", "quote_discount", "quote_total", "quote_pdf_url", "status"])
        return custom_order
