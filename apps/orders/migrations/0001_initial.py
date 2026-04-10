import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clients', '0001_initial'),
        ('products', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order_number', models.CharField(blank=True, max_length=20, unique=True, verbose_name='Buyurtma raqami')),
                ('status', models.CharField(choices=[('new', 'Yangi'), ('pending', 'Jarayonda'), ('production', 'Ishlab chiqarishda'), ('ready', 'Tayyor'), ('delivered', 'Yetkazildi'), ('completed', 'Yakunlandi'), ('cancelled', 'Bekor qilindi')], default='new', max_length=20, verbose_name='Holat')),
                ('payment_status', models.CharField(choices=[('unpaid', "To'lanmagan"), ('partial', "Qisman to'langan"), ('paid', "To'langan")], default='unpaid', max_length=20, verbose_name="To'lov holati")),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name='Jami summa')),
                ('paid_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14, verbose_name="To'langan summa")),
                ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=6, verbose_name='Chegirma (%)')),
                ('delivery_address', models.TextField(blank=True, verbose_name='Yetkazish manzili')),
                ('delivery_date', models.DateField(blank=True, null=True, verbose_name='Yetkazish sanasi')),
                ('notes', models.TextField(blank=True, verbose_name='Izoh')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='clients.client', verbose_name='Mijoz')),
                ('manager', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='managed_orders', to=settings.AUTH_USER_MODEL, verbose_name='Menejer')),
            ],
            options={
                'verbose_name': 'Buyurtma',
                'verbose_name_plural': 'Buyurtmalar',
                'ordering': ['-created_at'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='Miqdor')),
                ('price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Narx')),
                ('notes', models.CharField(blank=True, max_length=200, verbose_name='Izoh')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order', verbose_name='Buyurtma')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='products.product', verbose_name='Mahsulot')),
            ],
            options={
                'verbose_name': 'Buyurtma elementi',
                'verbose_name_plural': 'Buyurtma elementlari',
                'abstract': False,
            },
        ),
    ]
