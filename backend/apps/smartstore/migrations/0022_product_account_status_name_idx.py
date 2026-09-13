from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smartstore', '0021_alter_naveradproductreport_unique_together'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='smartstoreproduct',
            index=models.Index(fields=['account', 'status_type', 'name'], name='smartstore__acc_st_name_idx'),
        ),
    ]
