# Generated by Django 3.2.17 on 2023-02-03 13:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bus', '0003_alter_pikmessageexception_entity_uid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pikmessageexception',
            name='entity_uid',
            field=models.UUIDField(blank=True, null=True, verbose_name='Идентификатор сущности'),
        ),
        migrations.AlterUniqueTogether(
            name='pikmessageexception',
            unique_together={('queue', 'entity_uid')},
        ),
    ]