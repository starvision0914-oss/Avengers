from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('smartstore', '0007_add_naver_ai_keys'),
    ]

    operations = [
        migrations.AddField(
            model_name='smartstoreaccount',
            name='purchase_rate',
            field=models.IntegerField(default=0, help_text='구매가율(%) — 예: 70 입력 시 구매가=매출×70%'),
        ),
    ]
