import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- Order modeliga yetkazish manzili maydonlarini qo'shish ---
        migrations.AddField(
            model_name='order',
            name='delivery_region',
            field=models.CharField(blank=True, max_length=100, verbose_name='Viloyat'),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_district',
            field=models.CharField(blank=True, max_length=100, verbose_name='Tuman'),
        ),
        migrations.AddField(
            model_name='order',
            name='delivery_mfy',
            field=models.CharField(blank=True, max_length=100, verbose_name='MFY'),
        ),

        # --- Payment modelini yaratish ---
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Summa')),
                ('method', models.CharField(
                    choices=[
                        ('cash', 'Naqd'),
                        ('card', 'Karta'),
                        ('transfer', "Bank o'tkazma"),
                        ('other', 'Boshqa'),
                    ],
                    default='cash',
                    max_length=20,
                    verbose_name="To'lov turi",
                )),
                ('note', models.CharField(blank=True, max_length=200, verbose_name='Izoh')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Sana')),
                ('order', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='payments',
                    to='orders.order',
                    verbose_name='Buyurtma',
                )),
                ('received_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='received_payments',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Qabul qildi',
                )),
            ],
            options={
                'verbose_name': "To'lov",
                'verbose_name_plural': "To'lovlar",
                'ordering': ['-created_at'],
            },
        ),
    ]