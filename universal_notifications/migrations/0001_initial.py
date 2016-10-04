# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationHistory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('group', models.CharField(max_length=50)),
                ('klass', models.CharField(max_length=255)),
                ('receiver', models.CharField(max_length=255)),
                ('details', models.TextField()),
            ],
        ),
    ]
