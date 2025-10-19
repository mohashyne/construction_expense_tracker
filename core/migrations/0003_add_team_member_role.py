# Generated manually for adding team member role support

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_multitenant_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='role',
            name='is_team_member',
            field=models.BooleanField(default=False, help_text='For team member access'),
        ),
    ]
