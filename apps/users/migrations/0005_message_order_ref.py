from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('users', '0004_message'),
    ]
    operations = [
        migrations.AddField(
            model_name='message',
            name='order_ref',
            field=models.IntegerField(blank=True, null=True, verbose_name='Buyurtma ID'),
        ),
        migrations.AddField(
            model_name='message',
            name='is_order_notification',
            field=models.BooleanField(default=False, verbose_name='Buyurtma bildirishi'),
        ),
    ]