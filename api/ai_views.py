"""
e-Mebel CRM — AI Assistant (Groq API — BEPUL, tez)

Kalit olish (1 daqiqa):
    1. https://console.groq.com  →  ro'yxatdan o'ting
    2. "API Keys"  →  "Create API Key"
    3. .env ga qo'shing: GROQ_API_KEY=gsk_...

Kutubxona kerak emas — faqat requests ishlatiladi.
"""
import os
import json
import requests
import re
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsStaffMember
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from django.utils import timezone

from apps.orders.models import Order, Payment
from apps.clients.models import Client
from apps.products.models import Product
from apps.warehouse.models import Stock
from apps.users.models import User


# ── CRM konteksti ─────────────────────────────────────────────────────────────
def build_crm_context():
    today       = timezone.now().date()
    month_start = today.replace(day=1)

    debt_total = Order.objects.exclude(
        status__in=['cancelled', 'completed']
    ).aggregate(
        s=Sum(ExpressionWrapper(
            F('total_amount') - F('paid_amount'),
            output_field=DecimalField()
        ))
    )['s'] or 0

    recent_orders = list(
        Order.objects.select_related('client').order_by('-created_at')[:5]
        .values('order_number', 'client__name', 'status', 'total_amount', 'created_at')
    )
    for o in recent_orders:
        o['created_at']   = o['created_at'].strftime('%d.%m.%Y')
        o['total_amount'] = float(o['total_amount'])

    top_clients = list(
        Client.objects.annotate(spent=Sum('orders__total_amount'))
        .filter(spent__gt=0).order_by('-spent')[:5]
        .values('name', 'phone', 'spent')
    )
    for c in top_clients:
        c['spent'] = float(c['spent'] or 0)

    low_stock = list(
        Stock.objects.filter(quantity__lte=F('min_quantity'))
        .select_related('product').order_by('quantity')[:5]
        .values('product__name', 'quantity', 'min_quantity')
    )

    staff_list = list(
        User.objects.filter(role__in=['admin', 'manager', 'accountant', 'worker'], is_active=True)
        .values('id', 'username', 'first_name', 'last_name', 'role')
    )

    return {
        "sana": today.strftime('%d.%m.%Y'),
        "xodimlar": staff_list,
        "buyurtmalar": {
            "jami":  Order.objects.count(),
            "bu_oy": Order.objects.filter(created_at__date__gte=month_start).count(),
            "holat": {
                "yangi":    Order.objects.filter(status='new').count(),
                "jarayonda":Order.objects.filter(status='pending').count(),
                "ishlab":   Order.objects.filter(status='production').count(),
                "tayyor":   Order.objects.filter(status='ready').count(),
                "bekor":    Order.objects.filter(status='cancelled').count(),
            },
            "kechikkan": Order.objects.filter(
                delivery_date__lt=today,
                status__in=['new','pending','production','ready']
            ).count(),
        },
        "moliya": {
            "jami_tushum": float(
                Payment.objects.filter(is_confirmed=True)
                .aggregate(s=Sum('amount'))['s'] or 0
            ),
            "bu_oy_tushum": float(
                Payment.objects.filter(
                    is_confirmed=True, created_at__date__gte=month_start
                ).aggregate(s=Sum('amount'))['s'] or 0
            ),
            "umumiy_qarz": float(debt_total),
        },
        "mijozlar": {
            "jami":        Client.objects.filter(is_archived=False).count(),
            "bu_oy_yangi": Client.objects.filter(created_at__date__gte=month_start).count(),
        },
        "mahsulotlar": {
            "jami_faol":    Product.objects.filter(is_active=True).count(),
            "kam_stok_soni":Stock.objects.filter(quantity__lte=F('min_quantity')).count(),
        },
        "songi_buyurtmalar":   recent_orders,
        "top_mijozlar":        top_clients,
        "kam_stok_mahsulotlar":low_stock,
    }


# ── Groq API chaqiruvi ────────────────────────────────────────────────────────
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Bepul modellar — navbat bilan sinab ko'riladi
GROQ_MODELS = [
    "llama-3.3-70b-versatile",   # eng aqlli, bepul
    "llama-3.1-8b-instant",      # tez, engil
    "gemma2-9b-it",              # Google Gemma, bepul
    "mixtral-8x7b-32768",        # Mistral, bepul
]

SYSTEM_PROMPT = """Sen e-Mebel CRM tizimining AI yordamchisisisan.
Mebel do'koni boshqaruv tizimi uchun ishlaysan.

Har doim:
- O'zbek tilida javob ber
- Aniq va qisqa bo'l
- Raqamlarni 1,500,000 so'm formatida yoz
- Markdown ishlatma, faqat oddiy matn yoz

### ACTION PROPOSALS:
Agar foydalanuvchi biror amalni bajarishni so'rasa (masalan: xabar yuborish), javobing oxirida maxsus ACTION tegi bilan taklif ber.
Sintaksis: [[ACTION: type | param1: val | param2: val]]

Hozirgi mavjud harakatlar:
1. SEND_BROADCAST: hamma xodimlarga xabar yuborish. Parametrlar: body (xabar matni), target (doim 'staff').
   Misol: [[ACTION: SEND_BROADCAST | target: staff | body: Bugun soat 17:00 da majlis!]]

FAQAT foydalanuvchi so'rasagina harakat taklif qil.
"""


def call_groq(api_key, messages):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    last_error = "Noma'lum xato"

    for model in GROQ_MODELS:
        payload = {
            "model":       model,
            "messages":    messages,
            "max_tokens":  1200,
            "temperature": 0.7,
        }
        try:
            resp = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
            data = resp.json()

            if resp.status_code == 200:
                text = data['choices'][0]['message']['content']
                return text, model

            last_error = data.get('error', {}).get('message', str(resp.status_code))

            # Rate limit — boshqa modelda ham xuddi shunday bo'ladi
            if resp.status_code == 429:
                break

        except Exception as e:
            last_error = str(e)

    return None, last_error


# ── AI View ───────────────────────────────────────────────────────────────────
class AIAssistantView(APIView):
    permission_classes = [IsStaffMember]

    def post(self, request):
        message = request.data.get('message', '').strip()
        mode    = request.data.get('mode', 'chat')
        history = request.data.get('history', [])

        if not message:
            return Response({'error': "Xabar bo'sh"}, status=400)

        api_key = (
            getattr(settings, 'GROQ_API_KEY', None)
            or os.environ.get('GROQ_API_KEY', '')
        ).strip()

        if not api_key:
            return Response({'error': (
                "GROQ_API_KEY topilmadi.\n"
                "1) https://console.groq.com → ro'yxatdan o'ting\n"
                "2) API Keys → Create API Key\n"
                "3) .env ga: GROQ_API_KEY=gsk_..."
            )}, status=500)

        crm_data    = build_crm_context()
        context_str = json.dumps(crm_data, ensure_ascii=False, indent=2)

        mode_note = {
            'report': (
                "HISOBOT REJIMI: Batafsil hisobot tayyorla.\n"
                "Qoidalar:\n"
                "1. Har bir bo'lim ## sarlavha bilan boshlansin\n"
                "2. Raqamli ma'lumotlarni Markdown jadval ko'rinishida ber:\n"
                "   | Nomi | Qiymati | Izoh |\n"
                "   |------|---------|------|\n"
                "   | ... | ... | ... |\n"
                "3. Jadval ustunlari aniq va qisqa bo'lsin\n"
                "4. Oxirida ## Xulosa va tavsiyalar bo'limi qo'sh\n"
                "5. Markdown formatini to'liq ishlat (## sarlavha, | jadval |)"
            ),
            'advice': (
                "TAVSIYA REJIMI: Eng muhim 3-5 ta tavsiya ber. "
                "Har biri yangi qatorda, ✅ belgisi bilan boshlangsin. "
                "Har bir tavsiya qisqa va amaliy bo'lsin."
            ),
        }.get(mode, "CHAT REJIMI: Qisqa va aniq javob ber. Markdown ishlatma.")

        system_content = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Bugungi CRM ma'lumotlari:\n{context_str}\n\n"
            f"{mode_note}"
        )

        # OpenAI formatidagi xabarlar
        messages = [{"role": "system", "content": system_content}]
        for h in history[-8:]:
            role = h.get('role', '')
            content = h.get('content', '')
            if role in ('user', 'assistant') and content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        answer, model_or_err = call_groq(api_key, messages)

        if answer is None:
            return Response({'error': f"❌ {model_or_err}"}, status=500)

        # Action parsing
        actions = []
        action_matches = re.finditer(r'\[\[ACTION:\s*(.*?)\s*\]\]', answer)
        for m in action_matches:
            raw = m.group(1)
            parts = [p.strip() for p in raw.split('|')]
            if not parts: continue
            
            act_type = parts[0]
            params = {}
            for p in parts[1:]:
                if ':' in p:
                    k, v = p.split(':', 1)
                    params[k.strip()] = v.strip()
            
            actions.append({'type': act_type, 'data': params})
        
        # Clean answer from action tags
        clean_answer = re.sub(r'\[\[ACTION:.*?\]\]', '', answer).strip()

        return Response({
            'answer':  clean_answer,
            'actions': actions,
            'alerts':  _generate_alerts(crm_data),
            'context': crm_data,
        })


# ── Ogohlantirishlar ──────────────────────────────────────────────────────────
def _generate_alerts(data):
    alerts = []

    if data['buyurtmalar']['kechikkan'] > 0:
        alerts.append({
            'type': 'danger', 'icon': '⚠️',
            'text': f"{data['buyurtmalar']['kechikkan']} ta buyurtma muddati o'tib ketgan!",
        })
    if data['mahsulotlar']['kam_stok_soni'] > 0:
        names = [p['product__name'] for p in data['kam_stok_mahsulotlar'][:2]]
        extra = data['mahsulotlar']['kam_stok_soni'] - 2
        alerts.append({
            'type': 'warning', 'icon': '📦',
            'text': "Kam stok: " + ', '.join(names) + (f" va yana {extra} ta" if extra > 0 else ''),
        })
    if data['moliya']['umumiy_qarz'] > 5_000_000:
        alerts.append({
            'type': 'warning', 'icon': '💸',
            'text': f"Umumiy qarz: {data['moliya']['umumiy_qarz']:,.0f} so'm",
        })
    if data['buyurtmalar']['holat']['yangi'] >= 5:
        alerts.append({
            'type': 'info', 'icon': '🆕',
            'text': f"{data['buyurtmalar']['holat']['yangi']} ta yangi buyurtma kutilmoqda",
        })

    return alerts