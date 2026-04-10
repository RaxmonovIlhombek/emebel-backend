from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_add_client_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('body', models.TextField(verbose_name='Xabar matni')),
                ('is_read', models.BooleanField(default=False, verbose_name='O\'qildi')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Vaqt')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL, verbose_name='Yuboruvchi')),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to=settings.AUTH_USER_MODEL, verbose_name='Qabul qiluvchi')),
            ],
            options={
                'verbose_name': 'Xabar',
                'verbose_name_plural': 'Xabarlar',
                'ordering': ['created_at'],
            },
        ),
    ]