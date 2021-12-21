from django.db import migrations, models
import models_logging.models

class Migration(migrations.Migration):

    dependencies = [
        ('models_logging', '0006_auto_20211020_2036'),
    ]

    operations = [
        migrations.AlterField(
            model_name='change',
            name='changed_data',
            field=models.JSONField(
                blank=True,
                encoder=models_logging.models.get_encoder,
                null=True
            ),
        )
    ]
