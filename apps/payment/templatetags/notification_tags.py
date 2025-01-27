from django import template
from apps.payment.models import Transaction

register = template.Library()

@register.simple_tag(takes_context=True)
def notification_count(context):
    request = context['request']
    # Pastikan session sudah dibuat
    if not request.session.session_key:
        request.session.create()
        
    # Hitung transaksi yang memerlukan perhatian (pending/process) berdasarkan session_id
    return Transaction.objects.filter(
        session_id=request.session.session_key,
        transaction_status__in=['pending', 'process']
    ).count() 
