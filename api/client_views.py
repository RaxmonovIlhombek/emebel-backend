"""
e-Mebel CRM — Client Portal API
Mijoz o'z buyurtmalari, to'lovlari va katalogini ko'rishi uchun

URL lari (urls.py ga qo'shing):
    from .client_views import ClientDashboardView, ClientCatalogView, ClientOrderCreateView
    path('client/dashboard/', ClientDashboardView.as_view(),   name='api-client-dashboard'),
    path('client/catalog/',   ClientCatalogView.as_view(),     name='api-client-catalog'),
    path('client/order/',     ClientOrderCreateView.as_view(), name='api-client-order'),
"""
from django.db.models import Sum, Count
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


# ── Yordamchi ──────────────────────────────────────────────────────────────────
STATUS_LABELS = {
    'new':         {'label': 'Yangi',            'step': 1},
    'measured':    {'label': 'O\'lcham olindi',  'step': 2},
    'in_progress': {'label': 'Ishlab chiqarishda','step': 3},
    'production':  {'label': 'Ishlab chiqarishda','step': 3},
    'ready':       {'label': 'Tayyor',            'step': 4},
    'delivered':   {'label': 'Yetkazildi',        'step': 5},
    'completed':   {'label': 'Yakunlandi',        'step': 5},
    'cancelled':   {'label': 'Bekor qilindi',     'step': 0},
}

PAYMENT_LABELS = {
    'paid':    'To\'liq to\'langan',
    'partial': 'Qisman to\'langan',
    'unpaid':  'To\'lanmagan',
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Mijoz Dashboard
# GET /api/client/dashboard/
# ══════════════════════════════════════════════════════════════════════════════
class ClientDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'client':
            return Response({'error': 'Faqat mijozlar uchun'}, status=403)

        # Mijoz profili
        try:
            client = user.client_profile
        except Exception:
            return Response({'error': 'Mijoz profili topilmadi'}, status=404)

        orders = client.orders.exclude(status='cancelled').order_by('-created_at')

        # Umumiy statistika
        total_spent   = float(orders.aggregate(s=Sum('paid_amount'))['s'] or 0)
        total_debt    = sum(float(o.remaining_amount) for o in orders.filter(payment_status__in=['unpaid','partial']))
        active_orders = orders.filter(status__in=['new','measured','in_progress','production','ready']).count()
        total_orders  = orders.count()

        # Oxirgi 8 ta buyurtma — timeline bilan
        recent_orders = []
        for o in orders[:8]:
            st = STATUS_LABELS.get(o.status, {'label': o.status, 'step': 1})
            pct = int(float(o.paid_amount) / float(o.total_amount) * 100) if float(o.total_amount) > 0 else 0
            recent_orders.append({
                'id':             o.id,
                'order_number':   o.order_number,
                'status':         o.status,
                'status_label':   st['label'],
                'step':           st['step'],
                'payment_status': o.payment_status,
                'payment_label':  PAYMENT_LABELS.get(o.payment_status, o.payment_status),
                'total_amount':   float(o.total_amount),
                'paid_amount':    float(o.paid_amount),
                'remaining':      float(o.remaining_amount),
                'paid_pct':       pct,
                'delivery_date':  str(o.delivery_date) if o.delivery_date else None,
                'created_at':     o.created_at.strftime('%d.%m.%Y') if o.created_at else None,
                'manager_name':   o.manager.get_full_name() if o.manager else '—',
            })

        # So'nggi 6 to'lov
        recent_payments = []
        try:
            from apps.orders.models import Payment
            METHOD_LABELS = {'cash': 'Naqd', 'card': 'Karta', 'transfer': 'Bank o\'tkazma'}
            pays = Payment.objects.filter(order__client=client, is_confirmed=True).order_by('-created_at')[:6]
            for p in pays:
                recent_payments.append({
                    'amount':     float(p.amount),
                    'method':     METHOD_LABELS.get(p.method, p.method),
                    'order_num':  p.order.order_number if p.order else '—',
                    'created_at': p.created_at.strftime('%d.%m.%Y %H:%M') if p.created_at else None,
                })
        except Exception:
            pass

        return Response({
            'client': {
                'name':   client.name,
                'phone':  client.phone,
                'city':   client.city or '',
                'email':  client.email or '',
                'avatar': client.avatar.url if client.avatar else None,
            },
            'stats': {
                'total_orders':  total_orders,
                'active_orders': active_orders,
                'total_spent':   total_spent,
                'total_debt':    total_debt,
            },
            'recent_orders':   recent_orders,
            'recent_payments': recent_payments,
        })


# ══════════════════════════════════════════════════════════════════════════════
# 2. Mahsulot Katalogi (Mijoz uchun)
# GET /api/client/catalog/
# ══════════════════════════════════════════════════════════════════════════════
class ClientCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.orders.models import Product, Category
        products = Product.objects.filter(is_active=True).select_related('category').order_by('category', 'name')
        result = []
        for p in products:
            result.append({
                'id':            p.id,
                'name':          p.name,
                'description':   p.description or '',
                'selling_price': float(p.selling_price or 0),
                'material':      p.material or '',
                'color':         p.color or '',
                'dimensions':    p.dimensions or '',
                'category':      p.category.name if p.category else '',
                'image':         request.build_absolute_uri(p.image.url) if p.image else None,
            })
        return Response({'products': result})


# ══════════════════════════════════════════════════════════════════════════════
# 3. Buyurtma Yaratish (Mijoz tomonidan)
# POST /api/client/order/
# body: { items: [{product_id, quantity, note}], delivery_region, delivery_address, note }
# ══════════════════════════════════════════════════════════════════════════════
class ClientOrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.role != 'client':
            return Response({'error': 'Faqat mijozlar uchun'}, status=403)

        try:
            client = user.client_profile
        except Exception:
            return Response({'error': 'Mijoz profili topilmadi'}, status=404)

        from apps.orders.models import Order, OrderItem, Product
        import random, string

        data  = request.data
        items = data.get('items', [])
        if not items:
            return Response({'error': 'Kamida 1 ta mahsulot tanlang'}, status=400)

        # Jami summa hisoblash
        total = 0
        item_objs = []
        for it in items:
            try:
                prod = Product.objects.get(id=it['product_id'], is_active=True)
                qty  = int(it.get('quantity', 1))
                price = float(prod.selling_price or 0)
                total += price * qty
                item_objs.append({'product': prod, 'quantity': qty, 'price': price, 'note': it.get('note','')})
            except Product.DoesNotExist:
                return Response({'error': f"Mahsulot topilmadi: {it.get('product_id')}"}, status=400)

        # Tartib raqam
        suffix = ''.join(random.choices(string.digits, k=4))
        order_number = f"C{timezone.now().strftime('%y%m%d')}{suffix}"

        order = Order.objects.create(
            client          = client,
            order_number    = order_number,
            status          = 'new',
            payment_status  = 'unpaid',
            total_amount    = total,
            paid_amount     = 0,
            delivery_region = data.get('delivery_region', client.region or ''),
            notes           = data.get('note', ''),
        )

        for it in item_objs:
            OrderItem.objects.create(
                order    = order,
                product  = it['product'],
                quantity = it['quantity'],
                price    = it['price'],
            )

        return Response({
            'success':      True,
            'order_number': order_number,
            'order_id':     order.id,
            'total':        total,
        }, status=201)
