from rest_framework import viewsets, views, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import models
from django.db.models import Sum, Count, Max
from django.db.models.functions import TruncDate
from .models import CPCDailyCost, CPCDeposit, CPCTransaction
from .serializers import CPCDailyCostSerializer, CPCDepositSerializer, CPCTransactionSerializer


class CPCDailyCostViewSet(viewsets.ModelViewSet):
    queryset = CPCDailyCost.objects.select_related('seller').all()
    serializer_class = CPCDailyCostSerializer
    filterset_fields = ['seller', 'date']
    search_fields = ['seller__seller_id', 'seller__seller_name']
    ordering_fields = ['date', 'total_cost']


class CPCDepositViewSet(viewsets.ModelViewSet):
    queryset = CPCDeposit.objects.select_related('seller').all()
    serializer_class = CPCDepositSerializer
    filterset_fields = ['seller', 'deposit_date']


class CPCTransactionViewSet(viewsets.ModelViewSet):
    queryset = CPCTransaction.objects.select_related('seller').all()
    serializer_class = CPCTransactionSerializer
    filterset_fields = ['seller', 'category']
    ordering_fields = ['transaction_time', 'amount']


class CPCSummaryView(views.APIView):
    def get(self, request):
        date = request.query_params.get('date')
        qs = CPCDailyCost.objects.select_related('seller')
        if date:
            qs = qs.filter(date=date)
        summary = qs.values('seller__seller_id', 'seller__seller_name').annotate(
            total_cpc=Sum('cpc_cost'),
            total_ai=Sum('ai_cost'),
            total_cost=Sum('total_cost'),
            total_clicks=Sum('clicks'),
        ).order_by('seller__seller_id')

        deposits = {}
        for d in CPCDeposit.objects.values('seller__seller_id').annotate(latest_balance=Sum('balance')):
            deposits[d['seller__seller_id']] = d['latest_balance']

        result = []
        for s in summary:
            sid = s['seller__seller_id']
            s['balance'] = deposits.get(sid, 0)
            result.append(s)
        return Response(result)


class CPCChartView(views.APIView):
    def get(self, request):
        date = request.query_params.get('date')
        seller_id = request.query_params.get('seller')
        qs = CPCDailyCost.objects.all()
        if date:
            qs = qs.filter(date=date)
        if seller_id:
            qs = qs.filter(seller_id=seller_id)
        data = qs.values('date').annotate(
            total_cpc=Sum('cpc_cost'),
            total_ai=Sum('ai_cost'),
            total_cost=Sum('total_cost'),
        ).order_by('date')
        return Response(list(data))


from .models import CrawlerAccount, CrawlerLog, GmarketDepositSnapshot, ElevenCostHistory, GmarketSellerGrade, ElevenSellerGrade
from .serializers import CrawlerAccountSerializer, CrawlerLogSerializer, GmarketDepositSnapshotSerializer, ElevenCostHistorySerializer, GmarketGradeSerializer, ElevenGradeSerializer
import threading

class CrawlerAccountViewSet(viewsets.ModelViewSet):
    queryset = CrawlerAccount.objects.all()
    serializer_class = CrawlerAccountSerializer
    filterset_fields = ['platform', 'is_active', 'crawling_status']

class CrawlerLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CrawlerLogSerializer
    filterset_fields = ['platform', 'level', 'account_id']

    def get_queryset(self):
        return CrawlerLog.objects.all()[:200]

class GmarketSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GmarketDepositSnapshotSerializer
    filterset_fields = ['gmarket_id']
    pagination_class = None

    def get_queryset(self):
        qs = GmarketDepositSnapshot.objects.all()
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(collected_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(collected_at__date__lte=date_to)
        return qs

class ElevenCostViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ElevenCostHistorySerializer
    filterset_fields = ['seller_id', 'transaction_type']
    pagination_class = None

    def get_queryset(self):
        qs = ElevenCostHistory.objects.all()
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(transaction_datetime__date__gte=date_from)
        if date_to:
            qs = qs.filter(transaction_datetime__date__lte=date_to)
        return qs

class GmarketGradeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GmarketSellerGrade.objects.all()
    serializer_class = GmarketGradeSerializer
    filterset_fields = ['gmarket_id']

class ElevenGradeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ElevenSellerGrade.objects.all()
    serializer_class = ElevenGradeSerializer
    filterset_fields = ['eleven_id']

class GmarketSummaryView(views.APIView):
    """지마켓 광고비 요약 - ai100 /api/cpc/summary/ 호환"""
    def get(self, request):
        from datetime import datetime, timedelta
        import pytz
        kst = pytz.timezone('Asia/Seoul')

        date_str = request.query_params.get('date')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        if date_from and date_to:
            start = kst.localize(datetime.strptime(date_from, '%Y-%m-%d'))
            end = kst.localize(datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
        elif date_str:
            start = kst.localize(datetime.strptime(date_str, '%Y-%m-%d'))
            end = start + timedelta(days=1)
        else:
            from django.utils import timezone as tz
            today = tz.localdate()
            date_str = today.isoformat()
            start = kst.localize(datetime.combine(today, datetime.min.time()))
            end = start + timedelta(days=1)

        latest_ids = GmarketDepositSnapshot.objects.filter(
            collected_at__gte=start, collected_at__lt=end
        ).values('gmarket_id').annotate(
            latest_id=Max('id')
        ).values_list('latest_id', flat=True)

        sellers = []
        total_cpc = 0
        total_ai = 0
        total_usage = 0
        total_balance = 0

        # 광고상태, AI, 등급 미리 조회
        cpc_status_map = {}
        for s in GmarketCpcAdStatus.objects.all():
            cpc_status_map[s.gmarket_id] = {
                'cpc1_on': s.cpc1_on, 'cpc1_off': s.cpc1_off,
                'cpc2_on': s.cpc2_on, 'cpc2_off': s.cpc2_off,
            }
        ai_map = {}
        for a in GmarketAiAdSummary.objects.all():
            ai_map[a.gmarket_id] = {
                'actual_status': a.actual_status,
                'actual_reason': a.actual_reason,
                'button_status': a.button_status,
                'start_date': a.start_date,
            }
        grade_map = {}
        for g in GmarketSellerGrade.objects.order_by('-collected_at'):
            if g.gmarket_id not in grade_map:
                grade_map[g.gmarket_id] = {
                    'seller_grade': g.seller_grade,
                    'max_item_count': g.max_item_count,
                    'approval_status': g.approval_status,
                    'contact_expiry': g.contact_expiry,
                }

        for snap in GmarketDepositSnapshot.objects.filter(id__in=latest_ids).order_by('gmarket_id'):
            seller = {
                'seller_id': snap.gmarket_id,
                'seller_alias': snap.gmarket_id,
                'balance': snap.total_balance,
                'cpc_spend': snap.gmarket_cpc,
                'auction_cpc': snap.auction_cpc,
                'ai_spend': snap.ai_usage,
                'ad_total': snap.total_usage,
                'collected_at': snap.collected_at.isoformat() if snap.collected_at else '',
                'cpc_status': cpc_status_map.get(snap.gmarket_id),
                'ai_status': ai_map.get(snap.gmarket_id),
                'grade_info': grade_map.get(snap.gmarket_id),
            }
            sellers.append(seller)
            total_cpc += snap.gmarket_cpc
            total_ai += snap.ai_usage
            total_usage += snap.total_usage
            total_balance += snap.total_balance

        return Response({
            'date': date_str or (date_from + '~' + date_to if date_from else ''),
            'totals': {
                'cpc_spend': total_cpc,
                'ai_spend': total_ai,
                'ad_total': total_usage,
                'balance': total_balance,
            },
            'sellers': sellers,
        })

class ElevenSummaryView(views.APIView):
    """11번가 광고비 요약"""
    def get(self, request):
        from datetime import datetime, timedelta
        import pytz
        kst = pytz.timezone('Asia/Seoul')

        date_str = request.query_params.get('date')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        qs = ElevenCostHistory.objects.all()
        if date_from and date_to:
            start = kst.localize(datetime.strptime(date_from, '%Y-%m-%d'))
            end = kst.localize(datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
            qs = qs.filter(transaction_datetime__gte=start, transaction_datetime__lt=end)
        elif date_str:
            start = kst.localize(datetime.strptime(date_str, '%Y-%m-%d'))
            end = start + timedelta(days=1)
            qs = qs.filter(transaction_datetime__gte=start, transaction_datetime__lt=end)
        else:
            from django.utils import timezone as tz
            today = tz.localdate()
            start = kst.localize(datetime.combine(today, datetime.min.time()))
            end = start + timedelta(days=1)
            qs = qs.filter(transaction_datetime__gte=start, transaction_datetime__lt=end)

        # 계정별 집계
        seller_stats = qs.values('seller_id').annotate(
            cpc_total=Sum('amount', filter=models.Q(transaction_type='CPC')),
            charge_total=Sum('amount', filter=models.Q(transaction_type='CHARGE')),
            total_count=Count('id'),
        ).order_by('seller_id')

        # 계정별 최신 잔액
        sellers = []
        total_cpc = 0
        for s in seller_stats:
            cpc = abs(s['cpc_total'] or 0)
            charge = abs(s['charge_total'] or 0)
            # 최신 잔액
            latest = ElevenCostHistory.objects.filter(seller_id=s['seller_id']).order_by('-transaction_datetime').first()
            balance = latest.balance if latest else 0

            sellers.append({
                'seller_id': s['seller_id'],
                'cpc_spend': cpc,
                'charge': charge,
                'balance': balance,
                'tx_count': s['total_count'],
            })
            total_cpc += cpc

        return Response({
            'totals': {'cpc_spend': total_cpc, 'seller_count': len(sellers)},
            'sellers': sellers,
        })

from .models import GmarketAiAdSummary, St11AdofficeCampaign
from .serializers import GmarketAiSummarySerializer, St11CampaignSerializer

from .models import GmarketCpcAdStatus, Cpc2Schedule, Cpc2History, AiSchedule, TelegramConfig, TelegramRecipient, SellerGroup
from .serializers import CpcAdStatusSerializer, Cpc2ScheduleSerializer, Cpc2HistorySerializer, AiScheduleSerializer, TelegramConfigSerializer, TelegramRecipientSerializer, SellerGroupSerializer

class CpcAdStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GmarketCpcAdStatus.objects.all()
    serializer_class = CpcAdStatusSerializer

class Cpc2ScheduleViewSet(viewsets.ModelViewSet):
    queryset = Cpc2Schedule.objects.all()
    serializer_class = Cpc2ScheduleSerializer

class Cpc2HistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Cpc2History.objects.all()[:100]
    serializer_class = Cpc2HistorySerializer

class AiScheduleViewSet(viewsets.ModelViewSet):
    queryset = AiSchedule.objects.all()
    serializer_class = AiScheduleSerializer

class TelegramConfigViewSet(viewsets.ModelViewSet):
    queryset = TelegramConfig.objects.all()
    serializer_class = TelegramConfigSerializer

class TelegramRecipientViewSet(viewsets.ModelViewSet):
    queryset = TelegramRecipient.objects.all()
    serializer_class = TelegramRecipientSerializer

class SellerGroupViewSet(viewsets.ModelViewSet):
    queryset = SellerGroup.objects.all()
    serializer_class = SellerGroupSerializer

class TelegramSendView(views.APIView):
    def post(self, request):
        import requests as req
        config = TelegramConfig.objects.first()
        if not config or not config.bot_token:
            return Response({'error': '텔레그램 봇 토큰이 설정되지 않았습니다.'}, status=400)

        message = request.data.get('message', '')
        recipients = TelegramRecipient.objects.filter(is_active=True)
        sent = 0
        for r in recipients:
            try:
                req.post(f'https://api.telegram.org/bot{config.bot_token}/sendMessage',
                    json={'chat_id': r.chat_id, 'text': message, 'parse_mode': 'HTML'}, timeout=10)
                sent += 1
            except:
                pass
        return Response({'sent': sent})

class Cpc2ControlView(views.APIView):
    def post(self, request):
        import threading as th
        action = request.data.get('action', 'on')
        accounts = request.data.get('accounts')
        source = request.data.get('source', 'manual')
        def run():
            from crawlers.gmarket_cpc2_control_crawler import run_control
            run_control(action, source, account_filter=accounts)
        th.Thread(target=run, daemon=True).start()
        return Response({'status': 'started', 'action': action})

class AiControlView(views.APIView):
    def post(self, request):
        import threading as th
        action = request.data.get('action', 'on')
        accounts = request.data.get('accounts')
        source = request.data.get('source', 'manual')
        def run():
            from crawlers.gmarket_ai_control_crawler import run_control
            run_control(action, source, account_filter=accounts)
        th.Thread(target=run, daemon=True).start()
        return Response({'status': 'started', 'action': action})

class GmarketAiViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GmarketAiAdSummary.objects.all()
    serializer_class = GmarketAiSummarySerializer
    filterset_fields = ['gmarket_id', 'actual_status']

class St11CampaignViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = St11AdofficeCampaign.objects.all()
    serializer_class = St11CampaignSerializer
    filterset_fields = ['eleven_id', 'is_ai']

class CrawlTriggerView(views.APIView):
    def post(self, request):
        platform = request.data.get('platform', 'gmarket')
        crawl_type = request.data.get('type', 'cost')  # cost, grade, or ai
        accounts_filter = request.data.get('accounts')

        def run():
            if crawl_type == 'cpc_status':
                from crawlers.gmarket_cpc_status_crawler import run_all_accounts
            elif crawl_type == 'ai':
                if platform == 'gmarket':
                    from crawlers.gmarket_ai_crawler import run_all_accounts
                else:
                    from crawlers.eleven_ai_crawler import run_all_accounts
            elif crawl_type == 'grade':
                if platform == 'gmarket':
                    from crawlers.gmarket_grade_crawler import run_all_accounts
                else:
                    from crawlers.eleven_grade_crawler import run_all_accounts
            else:
                if platform == 'gmarket':
                    from crawlers.gmarket_crawler import run_all_accounts
                else:
                    from crawlers.eleven_crawler import run_all_accounts
            run_all_accounts(account_filter=accounts_filter)

        threading.Thread(target=run, daemon=True).start()
        return Response({'status': 'started', 'platform': platform, 'type': crawl_type})

from .models import CronSchedule

class CronScheduleViewSet(viewsets.ModelViewSet):
    queryset = CronSchedule.objects.all()
    serializer_class = None  # inline below

    def get_serializer_class(self):
        from rest_framework import serializers as sz
        class S(sz.ModelSerializer):
            class Meta:
                model = CronSchedule
                fields = '__all__'
        return S

class CronApplyView(views.APIView):
    """CronSchedule 테이블 기반으로 실제 crontab 적용"""
    def post(self, request):
        import subprocess
        schedules = CronSchedule.objects.all()
        lines = ['# Avengers 자동 수집 스케줄 (UI에서 관리)\n']
        for s in schedules:
            prefix = '' if s.is_active else '#'
            lines.append(f'{prefix}{s.cron_expr} {s.command}  # {s.display_name}\n')

        cron_content = ''.join(lines)
        proc = subprocess.run(['crontab', '-'], input=cron_content, capture_output=True, text=True)
        if proc.returncode != 0:
            return Response({'error': proc.stderr}, status=500)
        return Response({'applied': len(schedules), 'content': cron_content})

class AccountUnblockView(views.APIView):
    """차단된 계정 해제"""
    def post(self, request):
        from .models import CrawlerAccount
        account_id = request.data.get('id')
        if not account_id:
            return Response({'error': 'id 필요'}, status=400)
        try:
            acct = CrawlerAccount.objects.get(id=account_id)
            acct.crawling_status = '정상'
            acct.fail_count = 0
            acct.save()
            return Response({'unblocked': acct.login_id})
        except CrawlerAccount.DoesNotExist:
            return Response({'error': '계정 없음'}, status=404)
