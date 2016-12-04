# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('universal_notifications', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('notification_token', models.TextField()),
                ('device_id', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=True, help_text='Inactive devices will not be sent notifications')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('app_id', models.CharField(max_length=100)),
                ('platform', models.CharField(choices=[('ios', 'iOS'), ('gcm', 'Google Cloud Messagging (deprecated)'), ('fcm', 'Firebase Cloud Messaging')], max_length=10)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='devices')),
            ],
        ),
    ]
