from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse
from urllib.request import urlopen

from django.core.management.base import BaseCommand

from shop.models import Brand, Category, Product


class Command(BaseCommand):
    help = "Load sample products into the database"

    def add_arguments(self, parser):
        parser.add_argument("--source", help="Path or URL to JSON/CSV file", required=False)

    def handle(self, *args, **options):
        source = options.get("source")
        if source:
            data = self._load_from_source(source)
        else:
            data = self._default_seed()
        count = 0
        for product in data:
            category_name = product.get("category", "إكسسوارات")
            category, _ = Category.objects.get_or_create(name_ar=category_name)
            brand_name = product.get("brand")
            brand = None
            if brand_name:
                brand, _ = Brand.objects.get_or_create(name=brand_name)
            Product.objects.update_or_create(
                sku=product["sku"],
                defaults={
                    "name_ar": product.get("name_ar") or product.get("name") or product["sku"],
                    "price": product.get("price", 0),
                    "stock": product.get("stock", 0),
                    "category": category,
                    "brand": brand,
                    "images": product.get("images", []),
                    "specs": product.get("specs"),
                    "is_active": product.get("is_active", True),
                },
            )
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Loaded {count} products"))

    def _load_from_source(self, source: str) -> Iterable[dict]:
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            with urlopen(source, timeout=10) as response:  # nosec B310
                content = response.read()
        else:
            content = Path(source).read_bytes()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            reader = csv.DictReader(content.decode("utf-8").splitlines())
            return list(reader)

    def _default_seed(self) -> Iterable[dict]:
        return [
            {
                "sku": "LAP-001",
                "name_ar": "لابتوب أعمال 14 بوصة",
                "price": 650,
                "stock": 5,
                "category": "لابتوبات",
                "brand": "Lenovo",
                "images": [],
                "specs": {"ram": "8GB", "storage": "256GB SSD"},
            },
            {
                "sku": "DESK-101",
                "name_ar": "كمبيوتر مكتبي للألعاب",
                "price": 1200,
                "stock": 3,
                "category": "كمبيوترات مكتبية",
                "brand": "MSI",
                "images": [],
                "specs": {"gpu": "RTX 3060", "ram": "16GB"},
            },
            {
                "sku": "CCTV-5CAM",
                "name_ar": "حزمة 5 كاميرات مراقبة",
                "price": 900,
                "stock": 7,
                "category": "أنظمة المراقبة",
                "brand": "Hikvision",
                "images": [],
                "specs": {"resolution": "5MP", "storage": "2TB NVR"},
            },
            {
                "sku": "ACC-USB",
                "name_ar": "سلك HDMI احترافي",
                "price": 25,
                "stock": 50,
                "category": "إكسسوارات",
                "brand": "Anker",
                "images": [],
                "specs": {"length": "2m"},
            },
        ]
