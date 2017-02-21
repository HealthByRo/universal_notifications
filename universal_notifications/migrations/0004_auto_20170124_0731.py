# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.db.models.deletion
import universal_notifications.backends.twilio.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('universal_notifications', '0003_auto_20170112_0609'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnsubscribedUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, serialize=False, auto_created=True)),
                ('unsubscribed_from_all', models.BooleanField(default=False)),
                ('unsubscribed', universal_notifications.backends.twilio.fields.JSONField(default=dict)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='notificationhistory',
            name='category',
            field=models.CharField(max_length=255, default='system'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='phone',
            name='rate',
            field=models.IntegerField(verbose_name='Messages rate', default=6),
        ),
        migrations.AlterField(
            model_name='phonereceived',
            name='type',
            field=models.CharField(max_length=35, default='text', choices=[('voice', 'voice'), ('text', 'Text')]),
        ),
        migrations.AlterField(
            model_name='phonereceivedraw',
            name='status',
            field=models.CharField(max_length=35, db_index=True, default='pending', choices=[('pending', 'Pending'), ('pass', 'Pass'), ('fail', 'Fail'), ('rejected', 'Rejected')]),
        ),
        migrations.AlterField(
            model_name='phonesent',
            name='status',
            field=models.CharField(max_length=35, default='pending', choices=[('pending', 'Pending'), ('queued', 'Queued'), ('failed', 'failed'), ('sent', 'sent'), ('no_answer', 'no answer from twilio'), ('delivered', 'delivered'), ('undelivered', 'undelivered')]),
        ),
    ]
