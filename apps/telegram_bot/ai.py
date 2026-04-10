import os
import json
import requests
import re
import logging
from django.conf import settings
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.utils import timezone

from apps.orders.models import Order, Payment
from apps.clients.models import Client
from apps.products.models import Product
from apps.warehouse.models import Stock
from apps.users.models import User

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

SYSTEM_PROMPT = """Sen e-Mebel CRM tizimining AI yordamchisisisan.
Mebel do'koni boshqaruv tizimi uchun ishlaysan.
Telegram orqali xodimlar bilan muloqot qilyapsan.

Har doim:
- O'zbek tilida javob ber (agar foydalanuvchi boshqa tilda so'ramasa)
- Aniq va qisqa bo'l (Telegram ekraniga moslab)
- Raqamlarni 1,500,000 so'm formatida yoz
- HTML formatlashdan foydalanishing mumkin (<b>, <i>, <code>)
"""

def build_crm_context():
    """CRM dagi joriy holatni yig'ish."""
    today = timezone.now().date()
    month_start = today.replace(day=1)

    debt_total = Order.objects.exclude(
        status__in=['cancelled', 'completed']
    ).aggregate(
        s=Sum(ExpressionWrapper(
            F('total_amount') - F('paid_amount'),
            output_field=DecimalField()
        ))
    )['s'] or 0

    return {
        "sana": today.strftime('%d.%m.%Y'),
        "buyurtmalar": {
            "jami": Order.objects.count(),
            "bugun": Order.objects.filter(created_at__date=today).count(),
            "holat": {
                "yangi": Order.objects.filter(status='new').count(),
                "ishlab": Order.objects.filter(status='production').count(),
                "tayyor": Order.objects.filter(status='ready').count(),
            },
            "kechikkan": Order.objects.filter(
                delivery_date__lt=today,
                status__in=['new','pending','production','ready']
            ).count(),
        },
        "moliya": {
            "bugun_tushum": float(Payment.objects.filter(is_confirmed=True, created_at__date=today).aggregate(s=Sum('amount'))['s'] or 0),
            "bu_oy_tushum": float(Payment.objects.filter(is_confirmed=True, created_at__date__gte=month_start).aggregate(s=Sum('amount'))['s'] or 0),
            "umumiy_qarz": float(debt_total),
        },
        "mahsulotlar": {
            "kam_stok": Stock.objects.filter(quantity__lte=F('min_quantity')).count(),
        }
    }

def get_ai_response(message, chat_id=None):
    """Groq API orqali javob olish."""
    api_key = getattr(settings, 'GROQ_API_KEY', '').strip()
    if not api_key:
        return "❌ GROQ_API_KEY sozlanmagan."

    crm_data = build_crm_context()
    context_str = json.dumps(crm_data, ensure_ascii=False)

    messages = [
        {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nCRM Ma'lumotlari: {context_str}"},
        {"role": "user", "content": message}
    ]

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for model in GROQ_MODELS:
        try:
            resp = requests.post(GROQ_URL, json={
                "model": model,
                "messages": messages,
                "temperature": 0.5,
            }, headers=headers, timeout=20)
            if resp.ok:
                return resp.json()['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"AI Error: {e}")
            continue

    return "❌ AI bilan bog'lanishda xato yuz berdi."
