import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_alter_order_delivery_address'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='is_confirmed',
            field=models.BooleanField(default=False, verbose_name='Tasdiqlangan'),
        ),
        migrations.AddField(
            model_name='payment',
            name='submitted_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='submitted_payments',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Yubordi',
            ),
        ),
    ]