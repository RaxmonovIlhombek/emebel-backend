# from rest_framework import serializers
# from apps.users.models import User, Message
# from apps.clients.models import Client
# from apps.products.models import Category, Product
# from apps.orders.models import Order, OrderItem, Payment
# from apps.warehouse.models import Stock, StockMovement
#
#
# # ─── AUTH ───────────────────────────────────────────────
# class LoginSerializer(serializers.Serializer):
#     username = serializers.CharField()
#     password = serializers.CharField(write_only=True)
#
#
# class UserSerializer(serializers.ModelSerializer):
#     """
#     Frontendda ishlatiladigan barcha fieldlar:
#       - Staff.jsx  : is_active, last_login, date_joined, role
#       - Profile.jsx: avatar, phone, telegram_chat_id
#       - Messages   : id, username, first_name, last_name
#     """
#     full_name = serializers.SerializerMethodField()
#
#     def get_full_name(self, obj):
#         return obj.get_full_name() or obj.username
#
#     class Meta:
#         model = User
#         fields = [
#             'id', 'username', 'first_name', 'last_name', 'full_name',
#             'email', 'role', 'phone', 'avatar',
#             'telegram_chat_id', 'telegram_username',
#             'is_active',
#             'last_login',
#             'date_joined',
#         ]
#         read_only_fields = ['id', 'last_login', 'date_joined']
#
#
# # ─── CLIENTS ────────────────────────────────────────────
# class ClientSerializer(serializers.ModelSerializer):
#     total_orders = serializers.ReadOnlyField()
#     total_spent  = serializers.ReadOnlyField()
#
#     class Meta:
#         model = Client
#         fields = [
#             'id', 'name', 'phone', 'phone2', 'email',
#             'region', 'district', 'mfy', 'address', 'city',
#             'avatar', 'notes', 'is_archived',
#             'total_orders', 'total_spent',
#             'created_at',
#         ]
#         read_only_fields = ['id', 'created_at']
#
#
# # ─── PRODUCTS ───────────────────────────────────────────
# class CategorySerializer(serializers.ModelSerializer):
#     class Meta:
#         model  = Category
#         fields = ['id', 'name', 'slug', 'description']
#
#
# class ProductSerializer(serializers.ModelSerializer):
#     category_name  = serializers.CharField(source='category.name', read_only=True)
#     stock_quantity = serializers.ReadOnlyField()
#
#     class Meta:
#         model  = Product
#         fields = [
#             'id', 'name', 'sku', 'description', 'image',
#             'category', 'category_name',
#             'cost_price', 'selling_price',
#             'material', 'color', 'dimensions',
#             'is_active', 'stock_quantity',
#             'created_at',
#         ]
#         read_only_fields = ['id', 'created_at']
#
#
# # ─── ORDERS ─────────────────────────────────────────────
# class OrderItemSerializer(serializers.ModelSerializer):
#     product_name = serializers.CharField(source='product.name', read_only=True)
#     subtotal     = serializers.ReadOnlyField()
#
#     class Meta:
#         model  = OrderItem
#         fields = ['id', 'product', 'product_name', 'quantity', 'price', 'notes', 'subtotal']
#
#
# class PaymentSerializer(serializers.ModelSerializer):
#     received_by_name  = serializers.SerializerMethodField()
#     submitted_by_name = serializers.SerializerMethodField()
#
#     def get_received_by_name(self, obj):
#         if obj.received_by:
#             return obj.received_by.get_full_name() or obj.received_by.username
#         return None
#
#     def get_submitted_by_name(self, obj):
#         if obj.submitted_by:
#             return obj.submitted_by.get_full_name() or obj.submitted_by.username
#         return None
#
#     class Meta:
#         model  = Payment
#         fields = [
#             'id', 'amount', 'method', 'note',
#             'is_confirmed',
#             'received_by', 'received_by_name',
#             'submitted_by', 'submitted_by_name',
#             'created_at',
#         ]
#         read_only_fields = ['id', 'created_at']
#
#
# class OrderSerializer(serializers.ModelSerializer):
#     items                 = OrderItemSerializer(many=True, read_only=True)
#     payments              = PaymentSerializer(many=True, read_only=True)
#     client_name           = serializers.CharField(source='client.name',  read_only=True)
#     client_phone          = serializers.CharField(source='client.phone', read_only=True)
#     manager_name          = serializers.SerializerMethodField()
#     remaining_amount      = serializers.ReadOnlyField()
#     full_delivery_address = serializers.ReadOnlyField()
#
#     def get_manager_name(self, obj):
#         if obj.manager:
#             return obj.manager.get_full_name() or obj.manager.username
#         return None
#
#     class Meta:
#         model  = Order
#         fields = [
#             'id', 'order_number',
#             'client', 'client_name', 'client_phone',
#             'manager', 'manager_name',
#             'status', 'payment_status',
#             'total_amount', 'paid_amount', 'remaining_amount', 'discount',
#             'delivery_region', 'delivery_district', 'delivery_mfy',
#             'delivery_address', 'full_delivery_address',
#             'delivery_date', 'notes',
#             'items', 'payments',
#             'created_at', 'updated_at',
#         ]
#         read_only_fields = ['id', 'order_number', 'created_at', 'updated_at']
#
#
# class OrderCreateSerializer(serializers.ModelSerializer):
#     items = OrderItemSerializer(many=True)
#
#     class Meta:
#         model  = Order
#         fields = [
#             'client', 'manager',
#             'delivery_region', 'delivery_district',
#             'delivery_mfy', 'delivery_address',
#             'delivery_date', 'discount', 'notes',
#             'items',
#         ]
#
#     def create(self, validated_data):
#         from decimal import Decimal
#         items_data = validated_data.pop('items')
#         order      = Order.objects.create(**validated_data)
#         total      = Decimal('0')
#         for item_data in items_data:
#             item   = OrderItem.objects.create(order=order, **item_data)
#             total += item.subtotal
#         if order.discount:
#             total = total * (1 - order.discount / Decimal('100'))
#         order.total_amount = total
#         order.save()
#         return order
#
#
# # ─── WAREHOUSE ──────────────────────────────────────────
# class StockSerializer(serializers.ModelSerializer):
#     product_name     = serializers.CharField(source='product.name',           read_only=True)
#     product_sku      = serializers.CharField(source='product.sku',            read_only=True)
#     product_category = serializers.CharField(source='product.category.name',  read_only=True)
#     product_price    = serializers.DecimalField(source='product.selling_price',
#                            max_digits=14, decimal_places=2, read_only=True)
#     product_cost     = serializers.DecimalField(source='product.cost_price',
#                            max_digits=14, decimal_places=2, read_only=True)
#     is_low           = serializers.ReadOnlyField()
#
#     class Meta:
#         model  = Stock
#         fields = [
#             'id', 'product', 'product_name', 'product_sku', 'product_category',
#             'product_price', 'product_cost',
#             'quantity', 'min_quantity', 'is_low', 'updated_at',
#         ]
#
#
# class StockMovementSerializer(serializers.ModelSerializer):
#     product_name      = serializers.CharField(source='product.name', read_only=True)
#     product_sku       = serializers.CharField(source='product.sku',  read_only=True)
#     performed_by_name = serializers.SerializerMethodField()
#
#     def get_performed_by_name(self, obj):
#         if obj.performed_by:
#             return obj.performed_by.get_full_name() or obj.performed_by.username
#         return None
#
#     class Meta:
#         model  = StockMovement
#         fields = [
#             'id', 'product', 'product_name', 'product_sku',
#             'movement_type', 'quantity', 'reason',
#             'performed_by', 'performed_by_name',
#             'created_at',
#         ]
#         read_only_fields = ['id', 'created_at']
#
#
# # ─── MESSAGES ───────────────────────────────────────────
# class MessageSerializer(serializers.ModelSerializer):
#     """GET uchun — to'liq ma'lumot"""
#     sender_name   = serializers.SerializerMethodField()
#     receiver_name = serializers.SerializerMethodField()
#     sender_role   = serializers.CharField(source='sender.role',   read_only=True)
#     receiver_role = serializers.CharField(source='receiver.role', read_only=True)
#
#     def get_sender_name(self, obj):
#         return obj.sender.get_full_name() or obj.sender.username
#
#     def get_receiver_name(self, obj):
#         return obj.receiver.get_full_name() or obj.receiver.username
#
#     class Meta:
#         model  = Message
#         fields = [
#             'id',
#             'sender',   'sender_name',   'sender_role',
#             'receiver', 'receiver_name', 'receiver_role',
#             'body', 'is_read', 'order_ref',
#             'is_order_notification',
#             'created_at',
#         ]
#         read_only_fields = [
#             'id', 'sender', 'sender_name', 'sender_role',
#             'receiver_name', 'receiver_role',
#             'is_order_notification', 'is_read', 'created_at',
#         ]
#
#
# class MessageCreateSerializer(serializers.ModelSerializer):
#     """POST uchun — faqat receiver, body, order_ref"""
#     class Meta:
#         model  = Message
#         fields = ['receiver', 'body', 'order_ref']
#         extra_kwargs = {
#             'order_ref': {'required': False, 'allow_null': True},
#         }
#
#
# # ─── DASHBOARD ──────────────────────────────────────────
# class DashboardSerializer(serializers.Serializer):
#     total_orders        = serializers.IntegerField()
#     new_orders          = serializers.IntegerField()
#     total_clients       = serializers.IntegerField()
#     total_revenue       = serializers.DecimalField(max_digits=16, decimal_places=2)
#     total_debt          = serializers.DecimalField(max_digits=16, decimal_places=2)
#     low_stock_count     = serializers.IntegerField()
#     orders_by_status    = serializers.DictField()
#     status_distribution = serializers.DictField()
#     recent_orders       = OrderSerializer(many=True)
#     monthly_trend       = serializers.ListField()
#     payment_methods     = serializers.DictField()
#     top_clients         = serializers.ListField()
#     top_products        = serializers.ListField()
#     staff_activity      = serializers.ListField()




from rest_framework import serializers
from apps.users.models import User, Message
from apps.clients.models import Client
from apps.products.models import Category, Product
from apps.orders.models import Order, OrderItem, Payment
from apps.warehouse.models import Stock, StockMovement


# ─── AUTH ─────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    client_profile_name = serializers.CharField(source='client_profile.name', read_only=True)

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    class Meta:
        model  = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'role', 'phone', 'avatar', 'client_profile', 'client_profile_name',
            'telegram_chat_id', 'telegram_username',
            'is_active', 'last_login', 'date_joined',
        ]
        read_only_fields = ['id', 'last_login', 'date_joined', 'client_profile_name']


# ─── CLIENTS ──────────────────────────────────────────────────────────

class ClientSerializer(serializers.ModelSerializer):
    total_orders = serializers.ReadOnlyField()
    total_spent  = serializers.ReadOnlyField()

    class Meta:
        model  = Client
        fields = [
            'id', 'name', 'phone', 'phone2', 'email',
            'region', 'district', 'mfy', 'address', 'city',
            'avatar', 'notes', 'is_archived', 'archived_at',
            'total_orders', 'total_spent', 'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'archived_at']


# ─── PRODUCTS ─────────────────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model  = Category
        fields = ['id', 'name', 'slug', 'description', 'product_count']


class ProductSerializer(serializers.ModelSerializer):
    category_name  = serializers.CharField(source='category.name', read_only=True)
    stock_quantity = serializers.ReadOnlyField()

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'sku', 'description', 'image',
            'category', 'category_name',
            'cost_price', 'selling_price',
            'material', 'color', 'dimensions',
            'is_active', 'stock_quantity', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'worker':
            ret['cost_price'] = 0.0
        return ret


# ─── ORDERS ───────────────────────────────────────────────────────────

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtotal     = serializers.ReadOnlyField()

    class Meta:
        model  = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'notes', 'subtotal']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'worker':
            ret['price'] = 0.0
            ret['subtotal'] = 0.0
        return ret


class PaymentSerializer(serializers.ModelSerializer):
    received_by_name = serializers.SerializerMethodField()

    def get_received_by_name(self, obj):
        if obj.received_by:
            return obj.received_by.get_full_name() or obj.received_by.username
        return None

    class Meta:
        model  = Payment
        fields = [
            'id', 'amount', 'method', 'note',
            'is_confirmed', 'received_by', 'received_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class OrderSerializer(serializers.ModelSerializer):
    items                 = OrderItemSerializer(many=True, read_only=True)
    payments              = PaymentSerializer(many=True, read_only=True)
    client_name           = serializers.CharField(source='client.name', read_only=True)
    client_phone          = serializers.CharField(source='client.phone', read_only=True)
    manager_name          = serializers.SerializerMethodField()
    remaining_amount      = serializers.ReadOnlyField()
    full_delivery_address = serializers.ReadOnlyField()

    def get_manager_name(self, obj):
        if obj.manager:
            return obj.manager.get_full_name() or obj.manager.username
        return None

    def validate_delivery_date(self, value):
        import datetime
        from rest_framework.exceptions import ValidationError
        if value and value < datetime.date.today():
            raise ValidationError("Sanani o'tib ketgan kunga belgilash mumkin emas!")
        return value

    class Meta:
        model  = Order
        fields = [
            'id', 'order_number',
            'client', 'client_name', 'client_phone',
            'manager', 'manager_name',
            'status', 'payment_status',
            'total_amount', 'paid_amount', 'remaining_amount', 'discount',
            'delivery_region', 'delivery_district', 'delivery_mfy',
            'delivery_address', 'full_delivery_address',
            'delivery_date', 'notes',
            'items', 'payments',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'order_number', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'worker':
            for f in ['total_amount', 'paid_amount', 'remaining_amount', 'discount', 'payments']:
                if f in ret:
                    ret[f] = 0.0 if f != 'payments' else []
        return ret


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model  = Order
        fields = [
            'client', 'manager',
            'delivery_region', 'delivery_district', 'delivery_mfy', 'delivery_address',
            'delivery_date', 'discount', 'notes', 'items',
        ]
        extra_kwargs = {
            'client':  {'required': False, 'allow_null': True},
            'manager': {'required': False, 'allow_null': True},
        }

    def validate_delivery_date(self, value):
        import datetime
        from rest_framework.exceptions import ValidationError
        if value and value < datetime.date.today():
            raise ValidationError("Sanani o'tib ketgan kunga belgilash mumkin emas!")
        return value

    def create(self, validated_data):
        from decimal import Decimal
        items_data = validated_data.pop('items')
        order = Order.objects.create(**validated_data)
        total = Decimal('0')
        for item_data in items_data:
            item   = OrderItem.objects.create(order=order, **item_data)
            total += item.subtotal
        if order.discount:
            total = total * (1 - order.discount / Decimal('100'))
        order.total_amount = total
        order.save()
        return order


# ─── WAREHOUSE ────────────────────────────────────────────────────────

class StockSerializer(serializers.ModelSerializer):
    product_name     = serializers.CharField(source='product.name',           read_only=True)
    product_sku      = serializers.CharField(source='product.sku',            read_only=True)
    product_barcode  = serializers.CharField(source='product.barcode',        read_only=True, default='')
    product_category = serializers.CharField(source='product.category.name',  read_only=True, default='')
    product_price    = serializers.DecimalField(source='product.selling_price', max_digits=14, decimal_places=2, read_only=True)
    product_cost     = serializers.DecimalField(source='product.cost_price',    max_digits=14, decimal_places=2, read_only=True)
    is_low           = serializers.ReadOnlyField()

    class Meta:
        model  = Stock
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'product_barcode', 'product_category',
            'product_price', 'product_cost',
            'quantity', 'min_quantity', 'is_low', 'updated_at',
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'worker':
            ret['product_price'] = 0.0
            ret['product_cost'] = 0.0
        return ret


class StockMovementSerializer(serializers.ModelSerializer):
    product_name      = serializers.CharField(source='product.name',     read_only=True)
    product_sku       = serializers.CharField(source='product.sku',      read_only=True)
    performed_by_name = serializers.SerializerMethodField()

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return obj.performed_by.get_full_name() or obj.performed_by.username
        return None

    class Meta:
        model  = StockMovement
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'movement_type', 'quantity', 'reason',
            'performed_by', 'performed_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


# ─── MESSAGES ─────────────────────────────────────────────────────────

class MessageSerializer(serializers.ModelSerializer):
    sender_name   = serializers.SerializerMethodField()
    sender_role   = serializers.CharField(source='sender.role',   read_only=True)
    receiver_name = serializers.SerializerMethodField()
    receiver_role = serializers.CharField(source='receiver.role', read_only=True)

    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username

    def get_receiver_name(self, obj):
        return obj.receiver.get_full_name() or obj.receiver.username

    class Meta:
        model  = Message
        fields = [
            'id', 'sender', 'sender_name', 'sender_role',
            'receiver', 'receiver_name', 'receiver_role',
            'body', 'is_read', 'order_ref', 'is_order_notification', 'created_at',
        ]
        read_only_fields = ['id', 'sender', 'sender_name', 'sender_role',
                            'receiver_name', 'receiver_role', 'is_order_notification', 'created_at']


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Message
        fields = ['receiver', 'body', 'order_ref']
        extra_kwargs = {'order_ref': {'required': False, 'allow_null': True}}


# ─── DASHBOARD ────────────────────────────────────────────────────────

class DashboardSerializer(serializers.Serializer):
    total_orders    = serializers.IntegerField()
    new_orders      = serializers.IntegerField()
    total_clients   = serializers.IntegerField()
    total_revenue   = serializers.FloatField()
    total_debt      = serializers.FloatField()
    low_stock_count = serializers.IntegerField()
    orders_by_status = serializers.DictField()
    recent_orders   = OrderSerializer(many=True)