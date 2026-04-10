# api/views.py



from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from .permissions import IsStaffMember, IsAdmin, IsAdminOrManager, IsManagementStaff
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import authenticate
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField as DField
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from drf_spectacular.utils import (
    extend_schema, extend_schema_view,
    OpenApiParameter, OpenApiExample, OpenApiResponse,
    inline_serializer,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as drf_serializers

from apps.users.models import User, Message
from apps.clients.models import Client
from apps.products.models import Category, Product
from apps.orders.models import Order, OrderItem, Payment, Contract
from django.http import HttpResponse
from apps.warehouse.models import Stock, StockMovement

from .serializers import (
    LoginSerializer, UserSerializer,
    ClientSerializer, CategorySerializer, ProductSerializer,
    OrderSerializer, OrderCreateSerializer, PaymentSerializer,
    StockSerializer, StockMovementSerializer,
    MessageSerializer, MessageCreateSerializer,
)

from apps.telegram_bot.notify import (
    notify_new_registration,
    notify_password_reset_request,
    notify_new_order,
    notify_order_confirmed,
    notify_order_cancelled,
    notify_payment_confirmed
)


# ══════════════════ AUTH ══════════════════════════════════════════════

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        if not username or not password:
            return Response({'error': "Username va parol majburiy"}, status=400)
        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': "Username yoki parol noto'g'ri"}, status=400)
        if not user.is_active:
            return Response({'error': "Hisobingiz hali tasdiqlanmagan. Iltimos, admin faollashtirishini kuting."}, status=403)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'user': UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        return Response({'message': 'Chiqildi'})


class MeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        s = UserSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        if not username or not password:
            return Response({'error': 'Username va parol majburiy'}, status=400)
        if len(password) < 6:
            return Response({'error': 'Parol kamida 6 ta belgi'}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Bu username band'}, status=400)
        
        # Yangi foydalanuvchi faol emas — admin tasdiqlashi kerak
        user = User.objects.create_user(
            username   = username,
            password   = password,
            first_name = request.data.get('first_name', ''),
            last_name  = request.data.get('last_name', ''),
            phone      = request.data.get('phone') or None,
            role       = request.data.get('role', 'client'),
            client_profile_id = request.data.get('client_profile'),
            is_active  = False,
        )
        
        # Adminga xabar yuborish
        notify_new_registration(user)
        
        return Response({
            'message': 'Ro\'yxatdan o\'tdingiz! Admin tasdiqlashini kuting.',
            'user': UserSerializer(user).data
        }, status=201)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identity = request.data.get('identity', '').strip()
        if not identity:
            return Response({'error': "Username yoki telefon kiriting"}, status=400)
        
        notify_password_reset_request(identity)
        
        return Response({'message': "So'rov yuborildi. Admin tez orada bog'lanadi."})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old = request.data.get('old_password')
        new = request.data.get('new_password')
        if not old or not new:
            return Response({'error': 'old_password va new_password majburiy'}, status=400)
        if not request.user.check_password(old):
            return Response({'error': "Joriy parol noto'g'ri"}, status=400)
        if len(new) < 6:
            return Response({'error': 'Yangi parol kamida 6 ta belgi'}, status=400)
        request.user.set_password(new)
        request.user.save()
        Token.objects.filter(user=request.user).delete()
        token, _ = Token.objects.get_or_create(user=request.user)
        return Response({'message': "Parol o'zgartirildi", 'token': token.key})


# ══════════════════ DASHBOARD ═════════════════════════════════════════

class DashboardView(APIView):
    permission_classes = [IsStaffMember]

    def get(self, request):
        user    = request.user
        isAdmin = user.role in ['admin', 'manager', 'accountant']
        
        now         = timezone.now()
        today       = now.date()
        month_start = today.replace(day=1)

        # 1. Scoped Orders
        isWorker = user.role == 'worker'
        if isAdmin:
            orders = Order.objects.all()
        elif isWorker:
            # Workers see all orders (for processing) but we will mask financials
            orders = Order.objects.all()
        else:
            client_profile = getattr(user, 'client_profile', None)
            if not client_profile:
                return Response({
                    'total_orders': 0, 'active_orders': 0, 'total_revenue': 0,
                    'total_debt': 0, 'recent_orders': [], 'monthly_trend': [],
                    'is_client_view': True, 'client_name': user.get_full_name() or user.username
                })
            orders = Order.objects.filter(client=client_profile)

        # 2. Financials
        from django.db.models import ExpressionWrapper, DecimalField as DBDecimal
        
        total_revenue = float(orders.aggregate(s=Sum('paid_amount'))['s'] or 0)
        
        if isAdmin:
            total_debt = float(
                orders.filter(payment_status__in=['unpaid', 'partial'])
                .exclude(status='cancelled')
                .aggregate(d=Sum(F('total_amount') - F('paid_amount'), output_field=DField()))['d'] or 0
            )
        else:
            total_debt = float(
                orders.exclude(status='cancelled')
                .aggregate(d=Sum(F('total_amount') - F('paid_amount'), output_field=DField()))['d'] or 0
            )

        # 3. Counts & Statuses
        today_orders     = orders.filter(created_at__date=today).count()
        orders_by_status = {s[0]: orders.filter(status=s[0]).count() for s in Order.STATUS_CHOICES}
        recent           = orders.select_related('client', 'manager').order_by('-created_at')[:10]

        # 4. Monthly Trend
        from django.db.models.functions import TruncMonth
        from django.db.models import Count
        trend_months = 18 if isAdmin else 6
        start_trend = (today - timedelta(days=30 * trend_months)).replace(day=1)

        monthly_counts_qs = orders.filter(created_at__gte=start_trend).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(c=Count('id')).order_by('month')
        
        monthly_revs_qs = Payment.objects.filter(
            order__in=orders, created_at__gte=start_trend
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(s=Sum('amount')).order_by('month')

        counts_dict = {item['month'].strftime('%b %Y'): item['c'] for item in monthly_counts_qs if item['month']}
        revs_dict = {item['month'].strftime('%b %Y'): float(item['s']) for item in monthly_revs_qs if item['month']}

        monthly_trend = []
        for i in range(trend_months - 1, -1, -1):
            m_date = today.replace(day=1)
            for _ in range(i):
                try: m_date = (m_date - timedelta(days=1)).replace(day=1)
                except ValueError: pass
            
            key = m_date.strftime('%b %Y')
            monthly_trend.append({
                'month': key,
                'revenue': revs_dict.get(key, 0.0),
                'count': counts_dict.get(key, 0)
            })

        # 5. Base Response
        resp = {
            'total_orders':      orders.count(),
            'new_orders':        orders.filter(status='new').count(),
            'today_orders':      today_orders,
            'active_orders':     orders.exclude(status__in=['cancelled','completed']).count(),
            'total_revenue':     0 if isWorker else total_revenue,
            'total_debt':        0 if isWorker else total_debt,
            'status_distribution': orders_by_status,
            'recent_orders':     OrderSerializer(recent, many=True, context={'request': request}).data,
            'monthly_trend':     [] if isWorker else monthly_trend,
            'is_client_view':    not (isAdmin or isWorker)
        }

        # 6. Admin Only Data
        if isAdmin:
            # Stats calculation for Admin
            payment_methods = Payment.objects.aggregate(
                cash=Sum('amount', filter=Q(method='cash')),
                card=Sum('amount', filter=Q(method='card')),
                transfer=Sum('amount', filter=Q(method='transfer')),
                other=Sum('amount', filter=Q(method='other'))
            )
            payment_methods = {k: v or 0 for k, v in payment_methods.items()}

            top_products = list(
                Product.objects.annotate(
                    qty=Sum('orderitem__quantity'),
                    revenue=Sum(ExpressionWrapper(F('orderitem__price') * F('orderitem__quantity'), output_field=DBDecimal()))
                ).filter(qty__gt=0).order_by('-qty')[:8].values('id', 'name', 'qty', 'revenue')
            )

            # Low Stock
            low_stock_qs = Stock.objects.filter(quantity__lte=F('min_quantity')).select_related('product').order_by('quantity')[:8]
            low_stock_items = [{'id':s.id, 'name':s.product.name, 'quantity':float(s.quantity), 'unit':getattr(s.product,'unit','')} for s in low_stock_qs]

            # Sales Funnel
            funnel_total     = orders.filter(created_at__date__gte=month_start).count()
            funnel_active    = orders.filter(created_at__date__gte=month_start).exclude(status='cancelled').count()
            funnel_delivered = orders.filter(created_at__date__gte=month_start, status__in=['delivered','completed']).count()
            
            resp.update({
                'total_clients':     Client.objects.filter(is_archived=False).count(),
                'low_stock_count':   Stock.objects.filter(quantity__lte=F('min_quantity')).count(),
                'low_stock_items':   low_stock_items,
                'payment_methods':   payment_methods,
                'top_products':      top_products,
                'sales_funnel': [
                    {'label': 'Yangi',    'value': funnel_total,     'color': '#6366f1'},
                    {'label': 'Faol',     'value': funnel_active,    'color': '#f59e0b'},
                    {'label': 'Yetkazildi','value': funnel_delivered, 'color': '#059669'},
                ]
            })
        elif not isWorker:
            # Client Only Data
            client_profile = getattr(user, 'client_profile', None)
            if client_profile:
                resp['client_name'] = client_profile.name
            resp['featured_products'] = ProductSerializer(Product.objects.filter(is_active=True).order_by('?')[:4], many=True).data

        return Response(resp)


# ══════════════════ CLIENTS ══════════════════════════════════════════

class ClientListCreateView(generics.ListCreateAPIView):
    serializer_class   = ClientSerializer
    permission_classes = [IsStaffMember]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['name', 'phone', 'phone2', 'city', 'region']
    ordering_fields    = ['name', 'created_at']

    def get_queryset(self):
        qs       = Client.objects.all()
        archived = self.request.query_params.get('archived', 'false')
        return qs.filter(is_archived=(archived == 'true'))


class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Client.objects.all()
    serializer_class   = ClientSerializer
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAdminOrManager()]
        return [IsStaffMember()]


class ClientArchiveView(APIView):
    permission_classes = [IsAdminOrManager]

    def post(self, request, pk):
        try:
            client = Client.objects.get(pk=pk)
        except Client.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)
        if client.is_archived:
            client.is_archived = False
            client.archived_at = None
            client.save(update_fields=['is_archived', 'archived_at'])
            return Response({'status': 'restored'})
        else:
            client.archive()
            return Response({'status': 'archived'})


# ══════════════════ CATEGORIES & PRODUCTS ════════════════════════════

class CategoryListCreateView(generics.ListCreateAPIView):
    queryset           = Category.objects.annotate(product_count=Count('products'))
    serializer_class   = CategorySerializer
    permission_classes = [IsStaffMember]
    pagination_class   = None
    filter_backends    = [filters.SearchFilter]
    search_fields      = ['name']


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsStaffMember]


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    # MUHIM: Skanerlashda xatolik bo'lmasligi uchun 'sku' birinchi o'ringa qo'yildi
    search_fields = ['sku', 'name', 'material', 'color']
    ordering_fields = ['name', 'selling_price', 'created_at']

    # 30 talik limitni o'chirish:
    # pagination_class = None

    def get_queryset(self):
        # select_related ombor (stock) bilan ishlaganda tezlikni oshiradi
        qs = Product.objects.select_related('category').all()

        # Skanerlash yoki qidiruv uchun parametrni olish
        search_query = self.request.query_params.get('search')
        if search_query:
            # Agar skaner MEB-3274 kabi kodni o'qisa, uni aniq qidiradi
            return qs.filter(sku__iexact=search_query) | qs.filter(name__icontains=search_query)

        if self.request.query_params.get('category'):
            qs = qs.filter(category_id=self.request.query_params['category'])
        if self.request.query_params.get('active') == 'true':
            qs = qs.filter(is_active=True)

        return qs.order_by('-created_at')  # Yangi mahsulotlar tepada chiqadi

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Product.objects.select_related('category').all()
    serializer_class   = ProductSerializer
    permission_classes = [IsAuthenticated]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]


# ══════════════════ ORDERS ═══════════════════════════════════════════

class OrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['order_number', 'client__name', 'client__phone']
    ordering_fields    = ['created_at', 'total_amount', 'delivery_date']

    def get_serializer_class(self):
        return OrderCreateSerializer if self.request.method == 'POST' else OrderSerializer

    def get_queryset(self):
        qs = Order.objects.select_related('client', 'manager').prefetch_related('items__product', 'payments')
        if self.request.query_params.get('status'):
            qs = qs.filter(status=self.request.query_params['status'])
        if self.request.query_params.get('client'):
            qs = qs.filter(client_id=self.request.query_params['client'])
        
        user = self.request.user
        # Staff members (admin, manager, accountant, worker) see all orders.
        # Clients ONLY see their own orders.
        if user.role == 'client':
            # getattr ishlatamiz chunki Django OneToOneField None bo'lsa AttributeError bermaydi
            client_profile = getattr(user, 'client_profile', None)
            if client_profile is not None:
                qs = qs.filter(client=client_profile)
            else:
                return Order.objects.none()
        elif user.role not in ['admin', 'manager', 'accountant', 'worker']:
            # Noma'lum role — hech narsa ko'rsatmaymiz
            return Order.objects.none()
            
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        user = self.request.user
        extra = {}
        if user.role == 'client':
            client_profile = getattr(user, 'client_profile', None)
            if client_profile is not None:
                extra['client'] = client_profile
            else:
                from rest_framework.exceptions import ValidationError
                raise ValidationError("Mijoz profili topilmadi. Buyurtma berish uchun profil bo'lishi shart.")
            # Clients cannot set discounts or specific managers
            serializer.validated_data.pop('discount', None)
            serializer.validated_data.pop('manager', None)
            
        order = serializer.save(**extra)
        try:
            notify_new_order(order)
        except Exception:
            pass


class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Order.objects.select_related('client', 'manager').prefetch_related('items__product', 'payments')
    serializer_class   = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if user.role == 'client':
            # Django OneToOneField da hasattr() har doim True qaytaradi,
            # shuning uchun qiymatni aniq tekshiramiz
            client_profile = getattr(user, 'client_profile', None)
            if client_profile is None or obj.client_id != client_profile.pk:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("Bu buyurtmaga kirish huquqingiz yo'q.")
        return obj


class OrderContractView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
            user = request.user
            if user.role == 'client':
                client_profile = getattr(user, 'client_profile', None)
                if client_profile is None or order.client_id != client_profile.pk:
                    return Response({'error': 'Ruxsat yo\'q'}, status=403)
        except Order.DoesNotExist:
            return Response({'error': 'Buyurtma topilmadi'}, status=404)
        
        # Shartnomani olish yoki yaratish
        contract, created = Contract.objects.get_or_create(order=order)
        
        # PDF generatsiya qilish
        try:
            pdf_bytes = contract.generate_pdf()
        except Exception as e:
            return Response({'error': f'PDF yaratishda xato: {str(e)}'}, status=500)
            
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"Shartnoma_{contract.contract_number}.pdf"
        # Brauzerda ochilishi uchun 'inline', yuklab olish uchun 'attachment'
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class OrderStatusUpdateView(APIView):
    permission_classes = [IsStaffMember]

    def patch(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)

        new_status = request.data.get('status')
        valid = [s[0] for s in Order.STATUS_CHOICES]
        if new_status not in valid:
            return Response({'error': "Noto'g'ri holat: " + ', '.join(valid)}, status=400)

        old_status = order.status

        # Avtomatik ombor chiqimi: new → production
        if new_status == 'production' and old_status == 'new':
            from django.db import transaction
            insufficient = []
            for item in order.items.select_related('product'):
                try:
                    stk = Stock.objects.get(product=item.product)
                    if stk.quantity < item.quantity:
                        insufficient.append(
                            f"{item.product.name}: kerak {item.quantity}, mavjud {stk.quantity}"
                        )
                except Stock.DoesNotExist:
                    insufficient.append(f"{item.product.name}: omborda yo'q")

            if insufficient:
                return Response({'error': "Omborda yetarli mahsulot yo'q:\n" + "\n".join(insufficient)}, status=400)

            with transaction.atomic():
                for item in order.items.select_related('product'):
                    StockMovement.objects.create(
                        product=item.product, movement_type='out', quantity=item.quantity,
                        reason=f"Buyurtma #{order.order_number} avtomatik chiqim",
                        performed_by=request.user,
                    )

        # Ombor qaytarish: production → cancelled
        elif new_status == 'cancelled' and old_status == 'production':
            for item in order.items.select_related('product'):
                StockMovement.objects.create(
                    product=item.product, movement_type='in', quantity=item.quantity,
                    reason=f"Buyurtma #{order.order_number} bekor - qaytarish",
                    performed_by=request.user,
                )

        order.status = new_status
        order.save()

        try:
            if new_status == 'production' and old_status == 'new':
                notify_order_confirmed(order)
            elif new_status == 'cancelled':
                notify_order_cancelled(order)
        except Exception:
            pass

        return Response(OrderSerializer(order).data)


class PaymentCreateView(generics.CreateAPIView):
    serializer_class   = PaymentSerializer
    permission_classes = [IsManagementStaff]

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError as DRFValidationError
        order  = Order.objects.get(pk=self.kwargs['order_pk'])
        amount = Decimal(str(serializer.validated_data['amount']))

        already_paid = order.payments.filter(is_confirmed=True).aggregate(s=Sum('amount'))['s'] or Decimal('0')
        remaining    = order.total_amount - already_paid

        if remaining <= 0:
            raise DRFValidationError(f"Bu buyurtma allaqachon to'liq to'langan ({order.total_amount:,.0f} so'm).")
        if amount > remaining:
            raise DRFValidationError(
                f"To'lov summasi ({amount:,.0f} so'm) qolgan qarzdan ({remaining:,.0f} so'm) oshib ketmoqda."
            )

        payment = serializer.save(order=order, received_by=self.request.user, is_confirmed=True)

        total_paid = order.payments.filter(is_confirmed=True).aggregate(s=Sum('amount'))['s'] or 0
        order.paid_amount = total_paid
        order.payment_status = 'paid' if total_paid >= order.total_amount else 'partial' if total_paid > 0 else 'unpaid'
        order.save()

        try:
            notify_payment_confirmed(order, payment)
        except Exception:
            pass


# ══════════════════ WAREHOUSE ═════════════════════════════════════════

class StockListView(generics.ListAPIView):
    serializer_class   = StockSerializer
    permission_classes = [IsStaffMember]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['product__name', 'product__sku']
    ordering_fields    = ['product__name', 'quantity']

    def get_queryset(self):
        qs = Stock.objects.select_related('product__category')
        if self.request.query_params.get('low_stock') == 'true':
            qs = qs.filter(quantity__lte=F('min_quantity'))
        return qs


class StockUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            stock = Stock.objects.get(pk=pk)
        except Stock.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)
        min_q = request.data.get('min_quantity')
        if min_q is not None:
            stock.min_quantity = int(min_q)
            stock.save(update_fields=['min_quantity'])
        return Response(StockSerializer(stock).data)


class StockMovementListCreateView(generics.ListCreateAPIView):
    serializer_class   = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['product__name', 'product__sku', 'reason']
    ordering_fields    = ['created_at']

    def get_queryset(self):
        qs = StockMovement.objects.select_related('product', 'performed_by')
        if self.request.query_params.get('product'):
            qs = qs.filter(product_id=self.request.query_params['product'])
        if self.request.query_params.get('type'):
            qs = qs.filter(movement_type=self.request.query_params['type'])
        return qs

    def perform_create(self, serializer):
        serializer.save(performed_by=self.request.user)


# ══════════════════ FINANCE ══════════════════════════════════════════

class FinanceSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders      = Order.objects.all()
        today       = timezone.now().date()
        month_start = today.replace(day=1)
        year_start  = today.replace(month=1, day=1)

        total_revenue  = float(orders.aggregate(s=Sum('paid_amount'))['s'] or 0)
        total_debt     = sum(
            float(o.remaining_amount)
            for o in orders.filter(payment_status__in=['unpaid','partial']).exclude(status='cancelled')
                           .only('total_amount','paid_amount')
        )
        month_revenue  = float(orders.filter(created_at__date__gte=month_start).aggregate(s=Sum('paid_amount'))['s'] or 0)
        year_revenue   = float(orders.filter(created_at__date__gte=year_start).aggregate(s=Sum('paid_amount'))['s'] or 0)
        today_revenue  = float(orders.filter(created_at__date=today).aggregate(s=Sum('paid_amount'))['s'] or 0)

        payment_methods = list(Payment.objects.filter(is_confirmed=True)
                               .values('method').annotate(total=Sum('amount'), count=Count('id')))

        return Response({
            'total_revenue':   total_revenue,
            'total_debt':      total_debt,
            'month_revenue':   month_revenue,
            'year_revenue':    year_revenue,
            'today_revenue':   today_revenue,
            'total_orders':    orders.count(),
            'paid_orders':     orders.filter(payment_status='paid').count(),
            'partial_orders':  orders.filter(payment_status='partial').count(),
            'unpaid_orders':   orders.filter(payment_status='unpaid').count(),
            'payment_methods': payment_methods,
        })


class FinancePaymentsView(generics.ListAPIView):
    serializer_class   = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter, filters.OrderingFilter]
    search_fields      = ['order__order_number', 'order__client__name']
    ordering_fields    = ['created_at', 'amount']

    def get_queryset(self):
        qs = Payment.objects.select_related('order__client', 'received_by').filter(is_confirmed=True)
        if self.request.query_params.get('method'):
            qs = qs.filter(method=self.request.query_params['method'])
        if self.request.query_params.get('date_from'):
            qs = qs.filter(created_at__date__gte=self.request.query_params['date_from'])
        if self.request.query_params.get('date_to'):
            qs = qs.filter(created_at__date__lte=self.request.query_params['date_to'])
        return qs.order_by('-created_at')


class FinanceDebtsView(generics.ListAPIView):
    serializer_class   = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            payment_status__in=['unpaid', 'partial']
        ).exclude(status='cancelled').select_related('client', 'manager').order_by('-created_at')


class FinanceChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        today = timezone.now().date()
        data = []

        if period == 'week':
            # Oxirgi 7 kun (kunbay)
            for i in range(6, -1, -1):
                d = today - timedelta(days=i)
                payments = Payment.objects.filter(is_confirmed=True, created_at__date=d)
                data.append({
                    'label': d.strftime('%d-%b'),  # Masalan: "24-Mar"
                    'revenue': float(payments.aggregate(s=Sum('amount'))['s'] or 0),
                })

        elif period == 'year':
            # Oxirgi 12 oy (oybay)
            for i in range(11, -1, -1):
                # Har bir oyning boshini hisoblash
                first_of_this_month = today.replace(day=1)
                d = (first_of_this_month - timedelta(days=i * 30)).replace(day=1)
                m_start = d
                # Keyingi oyning birinchi kuni
                if m_start.month == 12:
                    m_end = m_start.replace(year=m_start.year + 1, month=1)
                else:
                    m_end = m_start.replace(month=m_start.month + 1)

                payments = Payment.objects.filter(
                    is_confirmed=True,
                    created_at__date__gte=m_start,
                    created_at__date__lt=m_end
                )
                data.append({
                    'label': m_start.strftime('%b %Y'),
                    'revenue': float(payments.aggregate(s=Sum('amount'))['s'] or 0),
                })

        else:  # 'month' (default) - Oxirgi 30 kunni 5 kunlik intervallarga bo'lib ko'rsatish
            for i in range(29, -1, -5):
                d_end = today - timedelta(days=i - 4 if i >= 4 else 0)
                d_start = today - timedelta(days=i)
                payments = Payment.objects.filter(
                    is_confirmed=True,
                    created_at__date__gte=d_start,
                    created_at__date__lte=d_end
                )
                data.append({
                    'label': f"{d_start.day}-{d_end.day} {d_start.strftime('%b')}",
                    'revenue': float(payments.aggregate(s=Sum('amount'))['s'] or 0),
                })

        return Response(data)

# ══════════════════ MESSAGES ═════════════════════════════════════════

class MessageListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return MessageCreateSerializer if self.request.method == 'POST' else MessageSerializer

    def get_queryset(self):
        user = self.request.user
        qs   = Message.objects.filter(Q(sender=user) | Q(receiver=user)
                                      ).select_related('sender','receiver').order_by('created_at')
        with_user = self.request.query_params.get('with')
        if with_user:
            qs = qs.filter(
                Q(sender=user, receiver_id=with_user) | Q(sender_id=with_user, receiver=user)
            )
        return qs

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)


class MessageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            msg = Message.objects.get(pk=pk, receiver=request.user)
        except Message.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)
        msg.is_read = True
        msg.save(update_fields=['is_read'])
        return Response(MessageSerializer(msg).data)

    def delete(self, request, pk):
        try:
            msg = Message.objects.get(pk=pk)
            if msg.sender != request.user and msg.receiver != request.user:
                return Response({'error': "Ruxsat yo'q"}, status=403)
        except Message.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)
        msg.delete()
        return Response(status=204)


class MessageMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = Message.objects.filter(receiver=request.user, is_read=False).update(is_read=True)
        return Response({'marked': count})


# ══════════════════ USERS ════════════════════════════════════════════

class UserListView(generics.ListAPIView):
    serializer_class   = UserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ['username', 'first_name', 'last_name', 'phone', 'email']

    def get_queryset(self):
        user = self.request.user
        qs   = User.objects.all()
        
        # Agar mijoz bo'lsa — faqat AKTIV xodimlarni ko'ra olsin
        if user.role == 'client':
            qs = qs.filter(role__in=['admin', 'manager', 'accountant', 'worker'], is_active=True)
        
        if self.request.query_params.get('role'):
            qs = qs.filter(role=self.request.query_params['role'])
        active = self.request.query_params.get('active')
        if active == 'true':
            qs = qs.filter(is_active=True)
        elif active == 'false':
            qs = qs.filter(is_active=False)
        return qs


class UserDetailView(APIView):
    permission_classes = [IsStaffMember]

    def get(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)
        return Response(UserSerializer(user).data)

    def patch(self, request, pk):
        if request.user.role != 'admin' and request.user.pk != pk:
            return Response({'error': "Ruxsat yo'q"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)
        s = UserSerializer(user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


class UserToggleActiveView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        if request.user.role != 'admin':
            return Response({'error': "Faqat admin"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)
        if user.pk == request.user.pk:
            return Response({'error': "O'zingizni bloklashingiz mumkin emas"}, status=400)
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        return Response({'is_active': user.is_active})

class OrderPaymentLinkView(APIView):
    """
    Buyurtma uchun Click/Payme linklarini qaytaradi.
    """
    def get(self, request, pk):
        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            return Response({'error': "Order not found"}, status=404)
        
        # Faqat o'z buyurtmasini yoki xodimlar ko'rishi mumkin
        if not request.user.is_staff_member and order.client.user_account != request.user:
            return Response({'error': "Permission denied"}, status=403)
            
        remaining = order.remaining_amount
        if remaining <= 0:
            return Response({'error': "Order already paid"}, status=400)
            
        from apps.payments.utils import generate_click_link, generate_payme_link
        
        return Response({
            'click_url': generate_click_link(order.id, remaining),
            'payme_url': generate_payme_link(order.id, remaining),
            'amount':    remaining
        })


class UserResetPasswordView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        if request.user.role != 'admin':
            return Response({'error': "Faqat admin"}, status=403)
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': 'Topilmadi'}, status=404)
        new_pwd = request.data.get('new_password', '')
        if len(new_pwd) < 6:
            return Response({'error': 'Parol kamida 6 ta belgi'}, status=400)
        user.set_password(new_pwd)
        user.save()
        return Response({'message': "Parol tiklandi"})