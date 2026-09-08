"""Contact-only abuse controls; database counters are shared by all workers."""
import secrets
import time
from datetime import timedelta
from ipaddress import ip_address, ip_network

from django.conf import settings
from django.core import signing
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac

from .models import ContactSubmissionGuard


class ContactRejected(Exception):
    def __init__(self, message, status=400):
        self.message = message
        self.status = status


def context(request):
    if 'contact_nonce' not in request.session:
        request.session['contact_nonce'] = secrets.token_urlsafe(24)
    return {
        'contact_started': signing.dumps({'nonce': request.session['contact_nonce'], 'time': time.time()}, salt='contact'),
    }


def client_ip(request):
    # Forwarded headers are accepted only from explicitly configured trusted peers.
    peer = ip_address(request.META.get('REMOTE_ADDR') or '0.0.0.0')
    trusted_peer = False
    for cidr in settings.CONTACT_TRUSTED_PROXY_CIDRS:
        try:
            if peer in ip_network(cidr):
                trusted_peer = True
                break
        except ValueError:
            continue

    if trusted_peer:
        forwarded_values = (
            request.META.get('HTTP_CF_CONNECTING_IP', ''),
            request.META.get('HTTP_X_REAL_IP', ''),
            request.META.get('HTTP_X_FORWARDED_FOR', '').split(',', 1)[0],
        )
        for value in forwarded_values:
            try:
                if value.strip():
                    return str(ip_address(value.strip()))
            except ValueError:
                continue
    return str(peer)


def claim(namespace, value, limit, seconds=900):
    now = timezone.now()
    key = salted_hmac('contact-' + namespace, value).hexdigest()

    ContactSubmissionGuard.objects.filter(expires_at__lte=now).delete()
    row, _ = ContactSubmissionGuard.objects.get_or_create(
        key=key, defaults={'expires_at': now + timedelta(seconds=seconds)}
    )
    # Conditional SQL increment prevents concurrent requests exceeding the limit.
    return bool(ContactSubmissionGuard.objects.filter(pk=row.pk, count__lt=limit).update(count=F('count') + 1))




def preflight(request):
    # The server cannot identify an individual machine behind shared Wi-Fi/NAT.
    # Use the signed, server-issued browser key so one user cannot block others.
    user_key = request.session.get('contact_nonce')
    if not user_key:
        raise ContactRejected('Unable to verify this submission. Please reload and try again.')
    if not claim('user', user_key, 5):
        raise ContactRejected('Too many submissions. Please try again in 15 minutes.', 429)
    if request.POST.get('company_website', '').strip():
        raise ContactRejected('Unable to verify this submission. Please reload and try again.')
    try:
        data = signing.loads(request.POST.get('contact_started', ''), salt='contact', max_age=3600)
        age = time.time() - data['time']
        valid = data['nonce'] == request.session.get('contact_nonce') and 3 <= age <= 3600
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise ContactRejected('Please wait at least 3 seconds after loading the form. Reload if it has expired.')
