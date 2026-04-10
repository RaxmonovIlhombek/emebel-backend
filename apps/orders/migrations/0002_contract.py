from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contract_number', models.CharField(blank=True, max_length=30, unique=True, verbose_name='Shartnoma raqami')),
                ('status', models.CharField(choices=[('draft','Qoralama'),('active','Faol'),('done','Bajarildi'),('cancelled','Bekor')], default='draft', max_length=20, verbose_name='Holat')),
                ('signed_date', models.DateField(blank=True, null=True, verbose_name='Imzolangan sana')),
                ('valid_until', models.DateField(blank=True, null=True, verbose_name='Amal qilish muddati')),
                ('terms', models.TextField(blank=True, verbose_name='Shartnoma shartlari')),
                ('notes', models.TextField(blank=True, verbose_name='Izoh')),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='contract', to='orders.order', verbose_name='Buyurtma')),
            ],
            options={'verbose_name': 'Shartnoma', 'verbose_name_plural': 'Shartnomalar', 'ordering': ['-created_at']},
        ),
    ]