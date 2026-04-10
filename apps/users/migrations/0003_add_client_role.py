from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0004_merge_0002_client_fields_0003_client_archive'),
        ('users', '0002_alter_user_date_joined_alter_user_email_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='client_profile',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='user_account',
                to='clients.client',
                verbose_name='Mijoz profili',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'Admin'),
                    ('manager', 'Menejer'),
                    ('accountant', 'Buxgalter'),
                    ('worker', 'Omborchi'),
                    ('client', 'Mijoz'),
                ],
                default='manager',
                max_length=20,
                verbose_name='Rol',
            ),
        ),
    ]