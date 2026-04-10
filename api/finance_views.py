"""
e-Mebel CRM — Finance API
Buxgalter paneli uchun keng qamrovli moliyaviy ma'lumotlar

URL lari (urls.py ga qo'shing):
    from .finance_views import FinanceSummaryView, FinancePaymentsView, FinanceDebtView, FinanceChartView

    path('finance/summary/',  FinanceSummaryView.as_view(),  name='api-finance-summary'),
    path('finance/payments/', FinancePaymentsView.as_view(), name='api-finance-payments'),
    path('finance/debts/',    FinanceDebtView.as_view(),     name='api-finance-debts'),
    path('finance/chart/',    FinanceChartView.as_view(),    name='api-finance-chart'),
"""
from decimal import Decimal
from datetime import date, timedelta
from calendar import monthrange

from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField, Avg
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsManagementStaff


# ── Yordamchi ──────────────────────────────────────────────────────────────────
def _dec(val):
    return float(val or 0)

def _month_range(year, month):
    first = date(year, month, 1)
    last  = date(year, month, monthrange(year, month)[1])
    return first, last


# ── 1. Umumiy moliyaviy xulosа ─────────────────────────────────────────────────
class FinanceSummaryView(APIView):
    permission_classes = [IsManagementStaff]

    def get(self, request):
        from apps.orders.models import Order, Payment, Expense

        today       = timezone.now().date()
        month_start = today.replace(day=1)
        year_start  = today.replace(month=1, day=1)

        # ── Tushum ──────────────────────────────────────────────────────────
        payments_qs = Payment.objects.filter(is_confirmed=True)

        total_revenue      = _dec(payments_qs.aggregate(s=Sum('amount'))['s'])
        month_revenue      = _dec(payments_qs.filter(created_at__date__gte=month_start).aggregate(s=Sum('amount'))['s'])
        year_revenue       = _dec(payments_qs.filter(created_at__date__gte=year_start).aggregate(s=Sum('amount'))['s'])
        today_revenue      = _dec(payments_qs.filter(created_at__date=today).aggregate(s=Sum('amount'))['s'])

        # O'tgan oy
        prev_month_start, prev_month_end = _month_range(
            today.year if today.month > 1 else today.year - 1,
            today.month - 1 if today.month > 1 else 12,
        )
        prev_month_revenue = _dec(
            payments_qs.filter(
                created_at__date__gte=prev_month_start,
                created_at__date__lte=prev_month_end,
            ).aggregate(s=Sum('amount'))['s']
        )
        revenue_growth = (
            round((month_revenue - prev_month_revenue) / prev_month_revenue * 100, 1)
            if prev_month_revenue > 0 else 0
        )

        # ── Xarajatlar (Expenses) ──────────────────────────────────────────
        expenses_qs = Expense.objects.all()
        total_expenses = _dec(expenses_qs.aggregate(s=Sum('amount'))['s'])
        month_expenses = _dec(expenses_qs.filter(date__gte=month_start).aggregate(s=Sum('amount'))['s'])

        expense_breakdown = list(
            expenses_qs.filter(date__gte=month_start)
            .values('category')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('-total')
        )
        for e in expense_breakdown:
            e['total'] = _dec(e['total'])

        # ── Net Profit (Sof foyda) ─────────────────────────────────────────
        total_net_profit = total_revenue - total_expenses
        month_net_profit = month_revenue - month_expenses
        
        prev_month_expenses = _dec(
            expenses_qs.filter(date__gte=prev_month_start, date__lte=prev_month_end)
            .aggregate(s=Sum('amount'))['s']
        )
        prev_month_profit = prev_month_revenue - prev_month_expenses
        profit_growth = (
            round((month_net_profit - prev_month_profit) / abs(prev_month_profit) * 100, 1)
            if prev_month_profit != 0 else 0
        )

        # ── To'lov usullari ──────────────────────────────────────────────────
        method_breakdown = list(
            payments_qs.filter(created_at__date__gte=month_start)
            .values('method')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('-total')
        )
        for m in method_breakdown:
            m['total'] = _dec(m['total'])

        # ── Qarzlar ──────────────────────────────────────────────────────────
        active_orders = Order.objects.exclude(status__in=['cancelled', 'completed'])
        debt_total = _dec(
            active_orders.aggregate(
                d=Sum(ExpressionWrapper(
                    F('total_amount') - F('paid_amount'),
                    output_field=DecimalField()
                ))
            )['d']
        )
        debt_count = active_orders.filter(paid_amount__lt=F('total_amount')).count()

        overdue_orders = active_orders.filter(
            delivery_date__lt=today,
            paid_amount__lt=F('total_amount'),
        )
        overdue_debt = _dec(
            overdue_orders.aggregate(
                d=Sum(ExpressionWrapper(
                    F('total_amount') - F('paid_amount'),
                    output_field=DecimalField()
                ))
            )['d']
        )

        # Debt aging groups
        d30 = today - timedelta(days=30)
        d60 = today - timedelta(days=60)
        
        aging = {
            '0_30':  _dec(active_orders.filter(created_at__date__gte=d30).aggregate(s=Sum(F('total_amount')-F('paid_amount')))['s']),
            '31_60': _dec(active_orders.filter(created_at__date__lt=d30, created_at__date__gte=d60).aggregate(s=Sum(F('total_amount')-F('paid_amount')))['s']),
            '61_plus': _dec(active_orders.filter(created_at__date__lt=d60).aggregate(s=Sum(F('total_amount')-F('paid_amount')))['s']),
        }

        # ── Buyurtmalar statistikasi ──────────────────────────────────────
        orders_month     = Order.objects.filter(created_at__date__gte=month_start)
        orders_month_sum = _dec(orders_month.aggregate(s=Sum('total_amount'))['s'])
        orders_cancelled = orders_month.filter(status='cancelled').count()
        orders_completed = Order.objects.filter(
            status='completed', updated_at__date__gte=month_start
        ).count()

        # ── O'rtacha buyurtma summasi ────────────────────────────────────
        avg_order = _dec(
            Order.objects.filter(status__in=['completed', 'delivered'])
            .aggregate(a=Avg('total_amount'))['a']
        )

        return Response({
            'revenue': {
                'total':        total_revenue,
                'year':         year_revenue,
                'month':        month_revenue,
                'today':        today_revenue,
                'prev_month':   prev_month_revenue,
                'growth':       revenue_growth,   # %
            },
            'debt': {
                'total':        debt_total,
                'count':        debt_count,
                'overdue':      overdue_debt,
                'overdue_count': overdue_orders.count(),
            },
            'orders': {
                'month_count':  orders_month.count(),
                'month_sum':    orders_month_sum,
                'cancelled':    orders_cancelled,
                'completed':    orders_completed,
                'avg_amount':   avg_order,
            },
            'method_breakdown': method_breakdown,
            'expenses': {
                'total': total_expenses,
                'month': month_expenses,
                'breakdown': expense_breakdown,
            },
            'net_profit': {
                'total':  total_net_profit,
                'month':  month_net_profit,
                'growth': profit_growth,
            },
            'debt_aging': aging,
            'period': {
                'today':       str(today),
                'month_start': str(month_start),
                'year_start':  str(year_start),
            },
        })


# ── 2. To'lovlar ro'yxati (filter + pagination) ───────────────────────────────
class FinancePaymentsView(APIView):
    permission_classes = [IsManagementStaff]

    def get(self, request):
        from apps.orders.models import Payment

        qs = Payment.objects.filter(is_confirmed=True).select_related(
            'order', 'order__client', 'received_by'
        ).order_by('-created_at')

        # ── Filterlar ─────────────────────────────────────────────────────
        date_from = request.query_params.get('date_from')
        date_to   = request.query_params.get('date_to')
        method    = request.query_params.get('method')
        search    = request.query_params.get('search', '').strip()

        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if method:
            qs = qs.filter(method=method)
        if search:
            qs = qs.filter(
                Q(order__order_number__icontains=search) |
                Q(order__client__name__icontains=search) |
                Q(note__icontains=search)
            )

        # ── Jami hisob ────────────────────────────────────────────────────
        total = _dec(qs.aggregate(s=Sum('amount'))['s'])

        # ── Pagination ────────────────────────────────────────────────────
        page     = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        total_count = qs.count()
        qs = qs[(page-1)*per_page : page*per_page]

        results = []
        for p in qs:
            results.append({
                'id':              p.id,
                'amount':          _dec(p.amount),
                'method':          p.method,
                'note':            p.note,
                'created_at':      p.created_at.strftime('%d.%m.%Y %H:%M'),
                'order_number':    p.order.order_number,
                'order_id':        p.order.id,
                'client_name':     p.order.client.name if p.order.client else '—',
                'received_by':     p.received_by.get_full_name() or p.received_by.username if p.received_by else '—',
            })

        return Response({
            'results':     results,
            'total':       total,
            'count':       total_count,
            'page':        page,
            'pages':       (total_count + per_page - 1) // per_page,
        })


# ── 3. Qarzlar ro'yxati ───────────────────────────────────────────────────────
class FinanceDebtView(APIView):
    permission_classes = [IsManagementStaff]

    def get(self, request):
        from apps.orders.models import Order

        today  = timezone.now().date()
        filter = request.query_params.get('filter', 'all')  # all | overdue | partial

        qs = Order.objects.exclude(
            status__in=['cancelled', 'completed']
        ).filter(
            paid_amount__lt=F('total_amount')
        ).select_related('client', 'manager').order_by('-created_at')

        if filter == 'overdue':
            qs = qs.filter(delivery_date__lt=today)
        elif filter == 'partial':
            qs = qs.filter(paid_amount__gt=0)

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(order_number__icontains=search) |
                Q(client__name__icontains=search)
            )

        results = []
        for o in qs:
            debt = float(o.total_amount) - float(o.paid_amount)
            paid_pct = round(float(o.paid_amount) / float(o.total_amount) * 100) if o.total_amount else 0
            overdue  = bool(o.delivery_date and o.delivery_date < today)
            results.append({
                'id':            o.id,
                'order_number':  o.order_number,
                'client_name':   o.client.name if o.client else '—',
                'client_phone':  o.client.phone if o.client else '—',
                'total_amount':  float(o.total_amount),
                'paid_amount':   float(o.paid_amount),
                'debt':          debt,
                'paid_pct':      paid_pct,
                'status':        o.status,
                'delivery_date': o.delivery_date.strftime('%d.%m.%Y') if o.delivery_date else None,
                'overdue':       overdue,
                'days_overdue':  (today - o.delivery_date).days if overdue and o.delivery_date else 0,
                'manager':       o.manager.get_full_name() or o.manager.username if o.manager else '—',
            })

        total_debt = sum(r['debt'] for r in results)
        return Response({
            'results':    results,
            'total_debt': total_debt,
            'count':      len(results),
        })


# ── 4. Grafik ma'lumotlari ────────────────────────────────────────────────────
class FinanceChartView(APIView):
    permission_classes = [IsManagementStaff]

    def get(self, request):
        from apps.orders.models import Payment, Order

        period = request.query_params.get('period', 'month')  # week | month | year

        today = timezone.now().date()

        if period == 'week':
            start = today - timedelta(days=6)
            payments = (
                Payment.objects.filter(is_confirmed=True, created_at__date__gte=start)
                .annotate(day=TruncDay('created_at'))
                .values('day').annotate(total=Sum('amount')).order_by('day')
            )
            # Bo'sh kunlarni to'ldirish
            data = {}
            for i in range(7):
                d = start + timedelta(days=i)
                data[str(d)] = 0
            for p in payments:
                data[str(p['day'].date())] = _dec(p['total'])
            chart = [{'label': k, 'value': v} for k, v in data.items()]

        elif period == 'year':
            start = today.replace(month=1, day=1)
            payments = (
                Payment.objects.filter(is_confirmed=True, created_at__date__gte=start)
                .annotate(month=TruncMonth('created_at'))
                .values('month').annotate(total=Sum('amount')).order_by('month')
            )
            data = {}
            for m in range(1, today.month + 1):
                label = date(today.year, m, 1).strftime('%b')
                data[label] = 0
            for p in payments:
                label = p['month'].strftime('%b')
                data[label] = _dec(p['total'])
            chart = [{'label': k, 'value': v} for k, v in data.items()]

        else:  # month — oxirgi 30 kun
            start = today - timedelta(days=29)
            payments = (
                Payment.objects.filter(is_confirmed=True, created_at__date__gte=start)
                .annotate(day=TruncDay('created_at'))
                .values('day').annotate(total=Sum('amount')).order_by('day')
            )
            data = {}
            for i in range(30):
                d = start + timedelta(days=i)
                data[str(d)] = 0
            for p in payments:
                data[str(p['day'].date())] = _dec(p['total'])
            chart = [{'label': k[-5:], 'value': v} for k, v in data.items()]

        # Buyurtmalar soni (bir xil period)
        orders_chart = (
            Order.objects.filter(created_at__date__gte=start)
            .annotate(day=TruncDay('created_at'))
            .values('day').annotate(cnt=Count('id')).order_by('day')
        )

        return Response({'chart': chart, 'period': period})


# ── 5. Xarajatlar (CRUD) ───────────────────────────────────────────────────────
class FinanceExpenseView(APIView):
    permission_classes = [IsManagementStaff]

    def get(self, request):
        from apps.orders.models import Expense
        from .finance_serializers import ExpenseSerializer

        qs = Expense.objects.all().select_related('performed_by')

        # Filterlar
        category  = request.query_params.get('category')
        date_from = request.query_params.get('date_from')
        date_to   = request.query_params.get('date_to')
        search    = request.query_params.get('search', '').strip()

        if category:  qs = qs.filter(category=category)
        if date_from: qs = qs.filter(date__gte=date_from)
        if date_to:   qs = qs.filter(date__lte=date_to)
        if search:    qs = qs.filter(note__icontains=search)

        total_amount = _dec(qs.aggregate(s=Sum('amount'))['s'])

        # Pagination
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 20))
        total_count = qs.count()
        qs = qs[(page-1)*per_page : page*per_page]

        serializer = ExpenseSerializer(qs, many=True)

        return Response({
            'results':   serializer.data,
            'total_sum': total_amount,
            'count':     total_count,
            'page':      page,
            'pages':     (total_count + per_page - 1) // per_page,
        })

    def post(self, request):
        from .finance_serializers import ExpenseSerializer
        serializer = ExpenseSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

    def delete(self, request):
        from apps.orders.models import Expense
        pk = request.data.get('id')
        if not pk: 
            return Response({'error': 'ID kerak'}, status=400)
        try:
            expense = Expense.objects.get(pk=pk)
            expense.delete()
            return Response({'status': 'deleted'})
        except Expense.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)