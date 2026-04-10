from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='region',
            field=models.CharField(blank=True, max_length=100, verbose_name='Viloyat'),
        ),
        migrations.AddField(
            model_name='client',
            name='district',
            field=models.CharField(blank=True, max_length=100, verbose_name='Tuman'),
        ),
        migrations.AddField(
            model_name='client',
            name='mfy',
            field=models.CharField(blank=True, max_length=100, verbose_name='MFY'),
        ),
        migrations.AddField(
            model_name='client',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='clients/', verbose_name='Rasm'),
        ),
        migrations.AlterField(
            model_name='client',
            name='address',
            field=models.TextField(blank=True, verbose_name="Ko'cha / uy"),
        ),
    ]