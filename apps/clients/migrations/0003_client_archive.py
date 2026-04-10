from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.AddField(model_name='client', name='is_archived',
            field=models.BooleanField(default=False, verbose_name='Arxivlangan')),
        migrations.AddField(model_name='client', name='archived_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Arxivlangan vaqt')),
        migrations.AddField(model_name='client', name='archived_name',
            field=models.CharField(blank=True, max_length=200, verbose_name='Arxivdagi ismi')),
        migrations.AddField(model_name='client', name='archived_phone',
            field=models.CharField(blank=True, max_length=20, verbose_name='Arxivdagi telefon')),
    ]