from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200, verbose_name='Ism familiya')),
                ('phone', models.CharField(max_length=20, verbose_name='Telefon')),
                ('phone2', models.CharField(blank=True, max_length=20, verbose_name="Qo'shimcha telefon")),
                ('email', models.EmailField(blank=True, verbose_name='Email')),
                ('address', models.TextField(blank=True, verbose_name='Manzil')),
                ('city', models.CharField(blank=True, max_length=100, verbose_name='Shahar')),
                ('notes', models.TextField(blank=True, verbose_name='Izoh')),
            ],
            options={
                'verbose_name': 'Mijoz',
                'verbose_name_plural': 'Mijozlar',
                'ordering': ['-created_at'],
                'abstract': False,
            },
        ),
    ]
