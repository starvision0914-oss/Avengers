import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.utils import timezone
from .models import EmailAccount, EmailMessage


def sync_inbox(account_id):
    account = EmailAccount.objects.get(id=account_id)
    mail = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
    mail.login(account.username, account.password)
    mail.select('INBOX')

    _, data = mail.search(None, 'ALL')
    uids = data[0].split()

    # Get last 50 emails
    recent_uids = uids[-50:] if len(uids) > 50 else uids
    synced = 0

    for uid in recent_uids:
        uid_int = int(uid)
        if EmailMessage.objects.filter(account=account, uid=uid_int).exists():
            continue

        _, msg_data = mail.fetch(uid, '(RFC822)')
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        subject = ''
        raw_subject = msg.get('Subject', '')
        if raw_subject:
            decoded = decode_header(raw_subject)
            subject = ''.join(
                part.decode(enc or 'utf-8') if isinstance(part, bytes) else part
                for part, enc in decoded
            )

        from_addr = msg.get('From', '')
        from_name = ''
        if '<' in from_addr:
            from_name = from_addr.split('<')[0].strip().strip('"')
            from_addr_clean = from_addr.split('<')[1].rstrip('>')
        else:
            from_addr_clean = from_addr

        date = None
        date_str = msg.get('Date')
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except Exception:
                date = timezone.now()

        body_text = ''
        body_html = ''
        has_attachment = False

        if msg.is_multipart():
            for part in msg.walk():
                ct = part.get_content_type()
                cd = str(part.get('Content-Disposition', ''))
                if 'attachment' in cd:
                    has_attachment = True
                elif ct == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
                elif ct == 'text/html':
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_html = payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body_text = payload.decode(msg.get_content_charset() or 'utf-8', errors='replace')

        EmailMessage.objects.create(
            account=account,
            message_id=msg.get('Message-ID', ''),
            uid=uid_int,
            folder='INBOX',
            subject=subject,
            from_addr=from_addr_clean,
            from_name=from_name,
            to_addrs=msg.get('To', '').split(','),
            cc_addrs=(msg.get('Cc', '') or '').split(','),
            date=date,
            snippet=body_text[:300] if body_text else '',
            body_text=body_text,
            body_html=body_html,
            has_attachment=has_attachment,
        )
        synced += 1

    mail.logout()
    account.last_synced_at = timezone.now()
    account.save()
    return synced


def send_email(account_id, to_addrs, subject, body_html, cc_addrs=None):
    account = EmailAccount.objects.get(id=account_id)

    msg = MIMEMultipart('alternative')
    msg['From'] = f'{account.display_name} <{account.email_address}>'
    msg['To'] = ', '.join(to_addrs)
    msg['Subject'] = subject
    if cc_addrs:
        msg['Cc'] = ', '.join(cc_addrs)

    msg.attach(MIMEText(body_html, 'html', 'utf-8'))

    if account.smtp_use_tls:
        server = smtplib.SMTP(account.smtp_host, account.smtp_port)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port)

    server.login(account.username, account.password)
    all_recipients = to_addrs + (cc_addrs or [])
    server.sendmail(account.email_address, all_recipients, msg.as_string())
    server.quit()
    return True
