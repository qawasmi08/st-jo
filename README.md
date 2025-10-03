# Strike Force Computers & CCTVs API

مشروع Django + DRF لمتجر "القوة الضاربة للكمبيوتر وأنظمة المراقبة". يوفر إدارة المنتجات والطلبات العادية والمخصصة مع توليد عرض سعر PDF وتهيئة للتشغيل عبر Docker.

## المتطلبات

- Docker و Docker Compose
- أو Python 3.11 مع PostgreSQL 15+ في حال التشغيل المحلي بدون Docker

## الإعداد السريع عبر Docker

1. انسخ ملف البيئة الافتراضي:
   ```bash
   cp .env.example .env
   ```
2. عدّل القيم حسب متطلباتك (قاعدة البيانات، بيانات S3، مفاتيح JWT...).
3. شغّل الخدمات:
   ```bash
   docker-compose up --build
   ```
4. أنشئ مستخدم مشرف:
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```
5. للدخول إلى لوحة الإدارة: http://localhost:8000/admin/

## التشغيل اليدوي (اختياري)

1. أنشئ بيئة افتراضية وثبّت المتطلبات:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. أنشئ ملف `.env` بناءً على `.env.example`.
3. نفّذ الهجرات وأنشئ مستخدمًا مشرفًا:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```
4. شغّل الخادم:
   ```bash
   python manage.py runserver
   ```

## السكربتات المفيدة

- تحميل بيانات مبدئية للمنتجات:
  ```bash
  python manage.py seed_products
  ```
  أو مع مصدر خارجي (CSV/JSON):
  ```bash
  python manage.py seed_products --source https://example.com/products.json
  ```

## نظرة على الـ API

- المصادقة: `POST /api/auth/token/`, `POST /api/auth/refresh/`
- المنتجات: `GET /api/products/`, `POST /api/products/`
- رفع الصور: `POST /api/uploads/image/`
- الطلبات العادية: `POST /api/standard-orders/`, `PATCH /api/standard-orders/{id}/status`
- الطلبات المخصصة: `POST /api/custom-orders/` بالإضافة إلى إجراءات المتابعة مثل الجدولة والموافقة وتوليد PDF

اللغة الافتراضية عربية مع اتجاه RTL، وتم ضبط CORS وJWT وتخزين الملفات على S3 عند تزويد بيانات الاتصال.
