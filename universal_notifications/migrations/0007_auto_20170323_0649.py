# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('universal_notifications', '0006_auto_20170323_0634'),
    ]

    operations = [
        migrations.AlterField(
            model_name='phonesent',
            name='sms_id',
            field=models.CharField(max_length=50, blank=True),
        ),
    ]
