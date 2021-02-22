# Generated by Django 3.0.3 on 2020-05-30 18:26

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('daseiner', '0006_auto_20200521_1731'),
    ]

    operations = [
        migrations.CreateModel(
            name='WaitingJudge',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('group_name', models.CharField(max_length=500)),
                ('create_date', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'waiting_judge',
            },
        ),
    ]
