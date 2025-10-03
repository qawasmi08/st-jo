# Generated manually for Strike Force project
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Brand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name_ar', models.CharField(max_length=255, unique=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='shop.category')),
            ],
            options={'ordering': ['name_ar'], 'verbose_name_plural': 'Categories'},
        ),
        migrations.CreateModel(
            name='Customer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('phone', models.CharField(max_length=20)),
                ('whatsapp', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('city', models.CharField(max_length=120)),
                ('notes', models.TextField(blank=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name_ar', models.CharField(max_length=255)),
                ('sku', models.CharField(max_length=50, unique=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('stock', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('images', models.JSONField(blank=True, default=list)),
                ('specs', models.JSONField(blank=True, null=True)),
                ('brand', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='shop.brand')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='shop.category')),
            ],
            options={'ordering': ['name_ar']},
        ),
        migrations.CreateModel(
            name='StandardOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('new', 'جديد'), ('confirmed', 'مؤكد'), ('ready_for_pickup', 'جاهز للاستلام'), ('completed', 'مكتمل'), ('cancelled', 'ملغى')], default='new', max_length=32)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('currency', models.CharField(default='JOD', max_length=8)),
                ('pickup_notes', models.TextField(blank=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='standard_orders', to='shop.customer')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='CustomOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('new', 'طلب جديد'), ('site_survey_scheduled', 'تم جدولة الزيارة'), ('surveyed', 'تمت المعاينة'), ('quote_sent', 'تم إرسال العرض'), ('approved', 'تمت الموافقة'), ('scheduled_install', 'تمت جدولة التركيب'), ('installed', 'تم التركيب'), ('handed_over', 'تم التسليم'), ('completed', 'مكتمل'), ('cancelled', 'ملغى')], default='new', max_length=32)),
                ('requirement_summary', models.TextField()),
                ('site_address', models.CharField(blank=True, max_length=255)),
                ('site_city', models.CharField(blank=True, max_length=120)),
                ('site_geo_lat', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('site_geo_lng', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('preferred_contact_time', models.CharField(blank=True, max_length=120)),
                ('attachments', models.JSONField(blank=True, default=list)),
                ('quote_subtotal', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('quote_discount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('quote_total', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('currency', models.CharField(default='JOD', max_length=8)),
                ('quote_pdf_url', models.URLField(blank=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_orders', to='shop.customer')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='StandardOrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qty', models.PositiveIntegerField()),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='shop.standardorder')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='order_items', to='shop.product')),
            ],
            options={'unique_together': {('order', 'product')}},
        ),
        migrations.CreateModel(
            name='CustomOrderLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_type', models.CharField(choices=[('product', 'منتج'), ('service', 'خدمة')], max_length=20)),
                ('name', models.CharField(max_length=255)),
                ('sku', models.CharField(blank=True, max_length=50)),
                ('qty', models.DecimalField(decimal_places=2, max_digits=10)),
                ('unit_price', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('custom_order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='shop.customorder')),
            ],
            options={'ordering': ['id']},
        ),
    ]
