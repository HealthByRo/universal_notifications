# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('universal_notifications', '0005_auto_20170316_1814'),
    ]

    operations = [
        migrations.AlterField(
            model_name='phonereceiver',
            name='number',
            field=models.CharField(max_length=20, unique=True, db_index=True),
        ),
    ]
