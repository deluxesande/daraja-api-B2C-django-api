# Generated by Django 5.0.2 on 2024-02-08 12:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mpesa_api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mpesatransaction',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Success', 'Success'), ('Failed', 'Failed')], default='Pending', max_length=20),
        ),
    ]