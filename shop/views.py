from __future__ import annotations

from django.core.files.storage import default_storage
from django.db.models import Prefetch
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Brand,
    Category,
    CustomOrder,
    CustomOrderStatus,
    Product,
    StandardOrder,
    StandardOrderStatus,
)
from .serializers import (
    BrandSerializer,
    CategorySerializer,
    CustomOrderLinesBulkSerializer,
    CustomOrderSerializer,
    ProductSerializer,
    StandardOrderSerializer,
    StandardOrderStatusSerializer,
)
from .services import generate_custom_order_quote_pdf


class PublicReadMixin:
    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return [IsAuthenticated()]


class CategoryViewSet(PublicReadMixin, viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()


class BrandViewSet(PublicReadMixin, viewsets.ModelViewSet):
    serializer_class = BrandSerializer
    queryset = Brand.objects.all()


class ProductViewSet(PublicReadMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all()
        if self.action in {"list"} or (self.action == "retrieve" and not self.request.user.is_authenticated):
            queryset = queryset.filter(is_active=True)
        sku = self.request.query_params.get("sku")
        if sku:
            queryset = queryset.filter(sku__iexact=sku)
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category_id=category)
        q = self.request.query_params.get("q")
        if q:
            queryset = queryset.filter(name_ar__icontains=q)
        return queryset.select_related("category", "brand")


class ProductImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("image")
        if not file_obj:
            return Response({"detail": "يرجى رفع ملف صورة"}, status=status.HTTP_400_BAD_REQUEST)
        path = default_storage.save(f"products/{file_obj.name}", file_obj)
        url = default_storage.url(path)
        return Response({"url": url})


class StandardOrderViewSet(PublicReadMixin, viewsets.ModelViewSet):
    serializer_class = StandardOrderSerializer

    def get_permissions(self):
        if self.action in {"create"}:
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        qs = (
            StandardOrder.objects.all()
            .select_related("customer")
            .prefetch_related("items__product")
            .order_by("-created_at")
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=["patch"], url_path="status", serializer_class=StandardOrderStatusSerializer)
    def set_status(self, request, pk=None):
        order = self.get_object()
        serializer = StandardOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_status = serializer.validated_data["status"]
        try:
            if target_status == StandardOrderStatus.CONFIRMED:
                order.confirm()
            elif target_status == StandardOrderStatus.READY:
                order.mark_ready()
            elif target_status == StandardOrderStatus.COMPLETED:
                order.complete()
            elif target_status == StandardOrderStatus.CANCELLED:
                order.cancel()
            else:
                return Response({"detail": "حالة غير مدعومة"}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        return Response(StandardOrderSerializer(order).data)


class CustomOrderViewSet(PublicReadMixin, viewsets.ModelViewSet):
    serializer_class = CustomOrderSerializer

    def get_permissions(self):
        if self.action in {"create"}:
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        qs = (
            CustomOrder.objects.all()
            .select_related("customer")
            .prefetch_related(Prefetch("lines"))
            .order_by("-created_at")
        )
        status_filter = self.request.query_params.get("status")
        city_filter = self.request.query_params.get("city")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if city_filter:
            qs = qs.filter(customer__city__iexact=city_filter)
        return qs

    @action(detail=True, methods=["post"], url_path="schedule-survey")
    def schedule_survey(self, request, pk=None):
        custom_order = self.get_object()
        try:
            custom_order.set_status(CustomOrderStatus.SURVEY_SCHEDULED, [CustomOrderStatus.NEW])
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomOrderSerializer(custom_order).data)

    @action(detail=True, methods=["post"], url_path="mark-surveyed")
    def mark_surveyed(self, request, pk=None):
        custom_order = self.get_object()
        try:
            custom_order.set_status(
                CustomOrderStatus.SURVEYED,
                [CustomOrderStatus.SURVEY_SCHEDULED],
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomOrderSerializer(custom_order).data)

    @action(detail=True, methods=["post"], url_path="lines/bulk-set", serializer_class=CustomOrderLinesBulkSerializer)
    def bulk_set_lines(self, request, pk=None):
        custom_order = self.get_object()
        serializer = CustomOrderLinesBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(custom_order=custom_order)
        custom_order.refresh_from_db()
        return Response(CustomOrderSerializer(custom_order).data)

    @action(detail=True, methods=["post"], url_path="generate-quote-pdf")
    def generate_quote_pdf(self, request, pk=None):
        custom_order = self.get_object()
        try:
            custom_order.require_lines_for_quote()
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        url = generate_custom_order_quote_pdf(custom_order)
        custom_order.refresh_from_db()
        return Response({"quote_pdf_url": url})

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        custom_order = self.get_object()
        try:
            custom_order.set_status(
                CustomOrderStatus.APPROVED,
                [CustomOrderStatus.QUOTE_SENT],
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomOrderSerializer(custom_order).data)

    @action(detail=True, methods=["post"], url_path="schedule-install")
    def schedule_install(self, request, pk=None):
        custom_order = self.get_object()
        try:
            custom_order.set_status(
                CustomOrderStatus.SCHEDULED_INSTALL,
                [CustomOrderStatus.APPROVED],
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomOrderSerializer(custom_order).data)

    @action(detail=True, methods=["post"], url_path="mark-installed")
    def mark_installed(self, request, pk=None):
        custom_order = self.get_object()
        try:
            custom_order.set_status(
                CustomOrderStatus.INSTALLED,
                [CustomOrderStatus.SCHEDULED_INSTALL],
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomOrderSerializer(custom_order).data)

    @action(detail=True, methods=["post"], url_path="handover")
    def handover(self, request, pk=None):
        custom_order = self.get_object()
        try:
            custom_order.set_status(
                CustomOrderStatus.HANDED_OVER,
                [CustomOrderStatus.INSTALLED],
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomOrderSerializer(custom_order).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        custom_order = self.get_object()
        try:
            custom_order.set_status(
                CustomOrderStatus.COMPLETED,
                [CustomOrderStatus.HANDED_OVER],
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomOrderSerializer(custom_order).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        custom_order = self.get_object()
        try:
            custom_order.set_status(
                CustomOrderStatus.CANCELLED,
                [
                    CustomOrderStatus.NEW,
                    CustomOrderStatus.SURVEY_SCHEDULED,
                    CustomOrderStatus.SURVEYED,
                    CustomOrderStatus.QUOTE_SENT,
                    CustomOrderStatus.APPROVED,
                    CustomOrderStatus.SCHEDULED_INSTALL,
                ],
            )
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomOrderSerializer(custom_order).data)
