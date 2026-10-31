from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('portfolio', '0014_stocknewsarticle_canonical_url_and_more')]
    operations = [migrations.AddField(
        model_name='stocknewsarticle', name='relevance_checked_at',
        field=models.DateTimeField(null=True, blank=True),
    )]
