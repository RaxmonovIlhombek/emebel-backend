from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100, verbose_name='Nomi')),
                ('slug', models.SlugField(blank=True, unique=True)),
                ('description', models.TextField(blank=True, verbose_name='Tavsif')),
            ],
            options={
                'verbose_name': 'Kategoriya',
                'verbose_name_plural': 'Kategoriyalar',
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200, verbose_name='Nomi')),
                ('sku', models.CharField(max_length=50, unique=True, verbose_name='Artikul')),
                ('description', models.TextField(blank=True, verbose_name='Tavsif')),
                ('image', models.ImageField(blank=True, null=True, upload_to='products/', verbose_name='Rasm')),
                ('cost_price', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Tan narxi')),
                ('selling_price', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Sotish narxi')),
                ('material', models.CharField(blank=True, max_length=100, verbose_name='Material')),
                ('color', models.CharField(blank=True, max_length=50, verbose_name='Rang')),
                ('dimensions', models.CharField(blank=True, max_length=100, verbose_name="O'lcham")),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='products', to='products.category', verbose_name='Kategoriya')),
            ],
            options={
                'verbose_name': 'Mahsulot',
                'verbose_name_plural': 'Mahsulotlar',
                'ordering': ['name'],
                'abstract': False,
            },
        ),
    ]
