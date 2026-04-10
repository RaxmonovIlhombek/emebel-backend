from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BotSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chat_id',    models.CharField(db_index=True, max_length=32, unique=True)),
                ('lang',       models.CharField(default='uz', max_length=4)),
                ('step',       models.CharField(blank=True, default='', max_length=64)),
                ('data',       models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'Bot sessiya', 'verbose_name_plural': 'Bot sessiyalar', 'ordering': ['-updated_at']},
        ),
        migrations.CreateModel(
            name='PaymeTransaction',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True)),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
                ('updated_at',   models.DateTimeField(auto_now=True)),
                ('amount',       models.DecimalField(decimal_places=2, max_digits=16)),
                ('payme_id',     models.CharField(blank=True, db_index=True, max_length=64)),
                ('status',       models.CharField(choices=[('pending','Kutilmoqda'),('paid',"To'langan"),('cancelled','Bekor'),('error','Xato')], default='pending', max_length=16)),
                ('create_time',  models.BigIntegerField(blank=True, null=True)),
                ('perform_time', models.BigIntegerField(blank=True, null=True)),
                ('cancel_time',  models.BigIntegerField(blank=True, null=True)),
                ('reason',       models.IntegerField(blank=True, null=True)),
                ('extra',        models.JSONField(blank=True, default=dict)),
                ('chat_id',      models.CharField(blank=True, max_length=32)),
                ('order',        models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='payme_transactions', to='orders.order')),
            ],
            options={'verbose_name': 'Payme tranzaksiya', 'verbose_name_plural': 'Payme tranzaksiyalar', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='ClickTransaction',
            fields=[
                ('id',                models.BigAutoField(auto_created=True, primary_key=True)),
                ('created_at',        models.DateTimeField(auto_now_add=True)),
                ('updated_at',        models.DateTimeField(auto_now=True)),
                ('amount',            models.DecimalField(decimal_places=2, max_digits=16)),
                ('click_trans_id',    models.CharField(blank=True, db_index=True, max_length=64)),
                ('merchant_trans_id', models.CharField(blank=True, max_length=64)),
                ('status',            models.CharField(choices=[('pending','Kutilmoqda'),('paid',"To'langan"),('cancelled','Bekor'),('error','Xato')], default='pending', max_length=16)),
                ('extra',             models.JSONField(blank=True, default=dict)),
                ('chat_id',           models.CharField(blank=True, max_length=32)),
                ('order',             models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='click_transactions', to='orders.order')),
            ],
            options={'verbose_name': 'Click tranzaksiya', 'verbose_name_plural': 'Click tranzaksiyalar', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='ScheduledMessage',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('chat_id',    models.CharField(max_length=32)),
                ('msg_type',   models.CharField(choices=[('delivery_reminder','Yetkazish eslatmasi'),('payment_reminder',"To'lov eslatmasi"),('order_status',"Holat o'zgarishi"),('daily_report','Kunlik hisobot'),('low_stock','Ombor ogohlantirishi'),('custom','Maxsus xabar')], default='custom', max_length=32)),
                ('text',       models.TextField()),
                ('buttons',    models.JSONField(blank=True, default=list)),
                ('send_at',    models.DateTimeField()),
                ('sent',       models.BooleanField(default=False)),
                ('sent_at',    models.DateTimeField(blank=True, null=True)),
                ('order',      models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='scheduled_messages', to='orders.order')),
            ],
            options={'verbose_name': 'Rejali xabar', 'verbose_name_plural': 'Rejali xabarlar', 'ordering': ['send_at']},
        ),
        migrations.AddIndex(
            model_name='scheduledmessage',
            index=models.Index(fields=['sent', 'send_at'], name='bot_sched_sent_idx'),
        ),
    ]