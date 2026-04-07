from rest_framework import serializers
from .models import EmailAccount, EmailMessage, EmailAttachment, EmailLabel


class EmailAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAccount
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}


class EmailAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailAttachment
        fields = '__all__'


class EmailLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLabel
        fields = '__all__'


class EmailMessageSerializer(serializers.ModelSerializer):
    attachments = EmailAttachmentSerializer(many=True, read_only=True)
    account_email = serializers.CharField(source='account.email_address', read_only=True)

    class Meta:
        model = EmailMessage
        fields = '__all__'


class EmailMessageListSerializer(serializers.ModelSerializer):
    account_email = serializers.CharField(source='account.email_address', read_only=True)

    class Meta:
        model = EmailMessage
        fields = ['id', 'account', 'account_email', 'folder', 'subject', 'from_addr', 'from_name', 'date', 'snippet', 'has_attachment', 'is_read', 'is_starred']
