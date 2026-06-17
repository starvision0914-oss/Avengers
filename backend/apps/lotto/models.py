from django.db import models


class LottoHistory(models.Model):
    drw_no = models.IntegerField(primary_key=True)
    drw_date = models.CharField(max_length=20, blank=True, default='')
    num1 = models.IntegerField()
    num2 = models.IntegerField()
    num3 = models.IntegerField()
    num4 = models.IntegerField()
    num5 = models.IntegerField()
    num6 = models.IntegerField()
    bonus = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lotto_history'
        ordering = ['drw_no']

    def numbers(self):
        return [self.num1, self.num2, self.num3, self.num4, self.num5, self.num6]


class LottoPrediction(models.Model):
    """저장된 AI 예측 스냅샷 — 대상 회차 추첨 후 등수 자동 판정."""
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    target_round = models.IntegerField(help_text='예측 대상 회차 번호')
    # combinations 예시:
    # [{"numbers":[3,12,16,27,40,45],"score":100,"reason":"..."}, ...]
    combinations = models.JSONField(help_text='예측 조합 리스트')
    score_threshold = models.IntegerField(default=0, help_text='검색에 사용된 타겟 점수')
    note = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        db_table = 'lotto_prediction'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['target_round'])]
