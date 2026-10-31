from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('bot', '0001_initial')]
    operations = [migrations.AddField(
        model_name='notificationdelivery', name='retry_not_before',
        field=models.DateTimeField(null=True, blank=True),
    )]
