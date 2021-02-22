# Generated by Django 3.0.3 on 2020-05-21 17:11

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('daseiner', '0003_auto_20200518_0022'),
    ]

    operations = [
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('create_date', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('title', models.CharField(default=None, max_length=500)),
            ],
            options={
                'db_table': 'question',
            },
        ),
        migrations.AddField(
            model_name='room',
            name='question',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='daseiner.Question'),
        ),
    ]