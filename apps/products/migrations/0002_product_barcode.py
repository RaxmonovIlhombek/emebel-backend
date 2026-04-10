from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='barcode',
            field=models.CharField(blank=True, help_text='EAN-13, QR yoki boshqa barcode raqami', max_length=100, verbose_name='Barcode'),
        ),
    ]