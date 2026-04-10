from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_message_order_ref'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='telegram_chat_id',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Telegram Chat ID'),
        ),
        migrations.AddField(
            model_name='user',
            name='telegram_username',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='Telegram Username (@siz)'),
        ),
    ]
