from rest_framework import viewsets, views, status
from rest_framework.response import Response
from .models import EmailAccount, EmailMessage, EmailLabel
from .serializers import EmailAccountSerializer, EmailMessageSerializer, EmailMessageListSerializer, EmailLabelSerializer
from . import services


class EmailAccountViewSet(viewsets.ModelViewSet):
    queryset = EmailAccount.objects.all()
    serializer_class = EmailAccountSerializer


class EmailMessageViewSet(viewsets.ModelViewSet):
    serializer_class = EmailMessageSerializer
    filterset_fields = ['account', 'folder', 'is_read', 'is_starred']
    search_fields = ['subject', 'from_addr', 'from_name']

    def get_queryset(self):
        return EmailMessage.objects.select_related('account').prefetch_related('attachments')

    def get_serializer_class(self):
        if self.action == 'list':
            return EmailMessageListSerializer
        return EmailMessageSerializer


class EmailLabelViewSet(viewsets.ModelViewSet):
    queryset = EmailLabel.objects.all()
    serializer_class = EmailLabelSerializer


class EmailSyncView(views.APIView):
    def post(self, request):
        account_id = request.data.get('account_id')
        if not account_id:
            return Response({'error': '계정을 선택해주세요.'}, status=400)
        try:
            synced = services.sync_inbox(account_id)
            return Response({'synced': synced})
        except Exception as e:
            return Response({'error': str(e)}, status=500)


class EmailSendView(views.APIView):
    def post(self, request):
        try:
            services.send_email(
                account_id=request.data['account_id'],
                to_addrs=request.data['to'],
                subject=request.data['subject'],
                body_html=request.data.get('body', ''),
                cc_addrs=request.data.get('cc'),
            )
            return Response({'sent': True})
        except Exception as e:
            return Response({'error': str(e)}, status=500)
