from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Sum
from .models import Order, OrderItem, Payment, Contract

STATUS_STYLES = {
    'new':        ('#1d4ed8', '#dbeafe', '🆕 Yangi'),
    'pending':    ('#92400e', '#fef3c7', '⏳ Jarayonda'),
    'production': ('#c2410c', '#ffedd5', '🔨 Ishlab chiqarish'),
    'ready':      ('#065f46', '#d1fae5', '✅ Tayyor'),
    'delivered':  ('#047857', '#d1fae5', '🚚 Yetkazildi'),
    'completed':  ('#374151', '#f3f4f6', '🏁 Yakunlandi'),
    'cancelled':  ('#991b1b', '#fee2e2', '❌ Bekor'),
}
PAYMENT_STYLES = {
    'unpaid':  ('#991b1b', '#fee2e2', "💸 To'lanmagan"),
    'partial': ('#92400e', '#fef3c7', "⚡ Qisman"),
    'paid':    ('#065f46', '#d1fae5', "💚 To'langan"),
}
METHOD_ICONS = {
    'cash': '💵 Naqd', 'card': '💳 Karta',
    'transfer': '🏦 O\'tkazma', 'other': '📋 Boshqa',
}


class OrderItemInline(admin.TabularInline):
    model           = OrderItem
    extra           = 0
    fields          = ['product', 'quantity', 'price', 'notes', 'subtotal_display']
    readonly_fields = ['subtotal_display']

    def subtotal_display(self, obj):
        if obj.pk:
            subtotal = '{:,.0f}'.format(float(obj.subtotal))
            return format_html(
                '<strong style="color:#059669;">{} so\'m</strong>',
                subtotal
            )
        return '—'
    subtotal_display.short_description = 'Jami'


class PaymentInline(admin.TabularInline):
    model           = Payment
    extra           = 0
    fields          = ['amount', 'method', 'note', 'is_confirmed', 'received_by', 'created_at']
    readonly_fields = ['created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('received_by')


class ContractInline(admin.StackedInline):
    model           = Contract
    extra           = 0
    max_num         = 1
    fields          = ['contract_number', 'status', 'signed_date', 'valid_until', 'terms', 'notes']
    readonly_fields = ['contract_number']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display   = [
        'number_tag', 'client_tag', 'manager_tag',
        'status_badge', 'payment_badge',
        'total_tag', 'remaining_tag',
        'delivery_tag', 'created_at',
    ]
    list_filter    = ['status', 'payment_status', 'created_at',
                      ('manager', admin.RelatedOnlyFieldListFilter)]
    search_fields  = ['order_number', 'client__name', 'client__phone']
    ordering       = ['-created_at']
    date_hierarchy = 'created_at'
    list_per_page  = 25
    inlines        = [OrderItemInline, PaymentInline, ContractInline]
    actions        = ['export_pdf', 'create_contract', 'mark_completed']

    fieldsets = (
        ('📋 Asosiy ma\'lumotlar', {
            'fields': ('order_number', 'client', 'manager', 'status', 'payment_status'),
        }),
        ('💰 Moliya', {
            'fields': (('total_amount', 'paid_amount', 'discount'),),
        }),
        ('📍 Yetkazib berish', {
            'fields': (
                'delivery_date',
                ('delivery_region', 'delivery_district'),
                ('delivery_mfy', 'delivery_address'),
            ),
        }),
        ('📝 Izoh', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['order_number']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('client', 'manager')

    # ── Columns ───────────────────────────────────────────────────────

    def number_tag(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-weight:700;'
            'color:#f97316;font-size:13px;">#{}</span>',
            obj.order_number
        )
    number_tag.short_description = '№'
    number_tag.admin_order_field = 'order_number'

    def client_tag(self, obj):
        return format_html(
            '<div style="line-height:1.4;">'
            '<strong style="color:#111;">{}</strong><br>'
            '<span style="font-size:11px;color:#6b7280;font-family:monospace;">📞 {}</span>'
            '</div>',
            obj.client.name, obj.client.phone
        )
    client_tag.short_description = 'Mijoz'

    def manager_tag(self, obj):
        if obj.manager:
            name = obj.manager.get_full_name() or obj.manager.username
            return format_html('<span style="color:#374151;font-size:12px;">👤 {}</span>', name)
        return mark_safe('<span style="color:#d1d5db;">—</span>')
    manager_tag.short_description = 'Menejer'

    def status_badge(self, obj):
        color, bg, label = STATUS_STYLES.get(obj.status, ('#374151', '#f3f4f6', obj.get_status_display()))
        return format_html(
            '<span style="background:{};color:{};padding:4px 10px;border-radius:20px;'
            'font-size:11px;font-weight:700;white-space:nowrap;">{}</span>',
            bg, color, label
        )
    status_badge.short_description = 'Holat'
    status_badge.admin_order_field = 'status'

    def payment_badge(self, obj):
        color, bg, label = PAYMENT_STYLES.get(obj.payment_status, ('#374151', '#f3f4f6', '?'))
        return format_html(
            '<span style="background:{};color:{};padding:4px 10px;border-radius:20px;'
            'font-size:11px;font-weight:700;white-space:nowrap;">{}</span>',
            bg, color, label
        )
    payment_badge.short_description = "To'lov"
    payment_badge.admin_order_field = 'payment_status'

    def total_tag(self, obj):
        total = '{:,.0f}'.format(float(obj.total_amount))
        return format_html(
            '<span style="font-weight:700;color:#111;">{} so\'m</span>',
            total
        )
    total_tag.short_description = 'Jami'
    total_tag.admin_order_field = 'total_amount'

    def remaining_tag(self, obj):
        rem = obj.remaining_amount
        if rem > 0:
            rem_str = '{:,.0f}'.format(float(rem))
            return format_html(
                '<span style="color:#dc2626;font-weight:700;">{} so\'m</span>',
                rem_str
            )
        return mark_safe('<span style="color:#10b981;font-weight:700;">✓ 0</span>')
    remaining_tag.short_description = 'Qarz'

    def delivery_tag(self, obj):
        if not obj.delivery_date:
            return mark_safe('<span style="color:#d1d5db;">—</span>')
        today = timezone.now().date()
        if obj.delivery_date < today and obj.status not in ('completed', 'delivered', 'cancelled'):
            return format_html(
                '<span style="color:#dc2626;font-weight:600;">⚠ {}</span>',
                obj.delivery_date.strftime('%d.%m.%Y')
            )
        return format_html(
            '<span style="color:#374151;">{}</span>',
            obj.delivery_date.strftime('%d.%m.%Y')
        )
    delivery_tag.short_description = 'Yetkazish'
    delivery_tag.admin_order_field = 'delivery_date'

    # ── Actions ───────────────────────────────────────────────────────

    @admin.action(description='📄 Buyurtma PDF chop etish')
    def export_pdf(self, request, queryset):
        from apps.telegram_bot.pdf_generator import generate_order_pdf
        if queryset.count() == 1:
            order = queryset.first()
            pdf   = generate_order_pdf(order)
            resp  = HttpResponse(pdf, content_type='application/pdf')
            resp['Content-Disposition'] = f'attachment; filename="order_{order.order_number}.pdf"'
            return resp
        self.message_user(request, "Faqat bitta buyurtma tanlang!", level='warning')

    @admin.action(description='📝 Shartnoma yaratish')
    def create_contract(self, request, queryset):
        created = 0
        for order in queryset:
            contract, is_new = Contract.objects.get_or_create(order=order)
            if is_new:
                created += 1
        self.message_user(request, f'{created} ta shartnoma yaratildi.')

    @admin.action(description='✅ Yakunlandi deb belgilash')
    def mark_completed(self, request, queryset):
        count = queryset.filter(status__in=['delivered', 'ready']).update(status='completed')
        self.message_user(request, f'{count} ta buyurtma yakunlandi.')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display   = [
        'order_tag', 'client_tag', 'amount_tag',
        'method_tag', 'confirmed_tag', 'received_by_tag', 'created_at',
    ]
    list_filter    = ['method', 'is_confirmed', 'created_at']
    search_fields  = ['order__order_number', 'order__client__name']
    ordering       = ['-created_at']
    date_hierarchy = 'created_at'
    list_per_page  = 30
    readonly_fields = ['created_at']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order__client', 'received_by')

    def order_tag(self, obj):
        return format_html(
            '<span style="font-family:monospace;color:#f97316;font-weight:700;">#{}</span>',
            obj.order.order_number
        )
    order_tag.short_description = 'Buyurtma'

    def client_tag(self, obj):
        return format_html('<span style="color:#374151;">{}</span>', obj.order.client.name)
    client_tag.short_description = 'Mijoz'

    def amount_tag(self, obj):
        amount = '{:,.0f}'.format(float(obj.amount))
        return format_html(
            '<strong style="color:#059669;font-size:14px;">+{} so\'m</strong>',
            amount
        )
    amount_tag.short_description = 'Summa'
    amount_tag.admin_order_field = 'amount'

    def method_tag(self, obj):
        label = METHOD_ICONS.get(obj.method, obj.get_method_display())
        return format_html('<span style="color:#374151;">{}</span>', label)
    method_tag.short_description = "To'lov turi"

    def confirmed_tag(self, obj):
        if obj.is_confirmed:
            return mark_safe(
                '<span style="background:#d1fae5;color:#065f46;padding:3px 10px;'
                'border-radius:20px;font-size:11px;font-weight:700;">✓ Tasdiqlangan</span>'
            )
        return mark_safe(
            '<span style="background:#fef3c7;color:#92400e;padding:3px 10px;'
            'border-radius:20px;font-size:11px;">⏳ Kutilmoqda</span>'
        )
    confirmed_tag.short_description = 'Holat'

    def received_by_tag(self, obj):
        if obj.received_by:
            name = obj.received_by.get_full_name() or obj.received_by.username
            return format_html('<span style="color:#374151;">👤 {}</span>', name)
        return mark_safe('<span style="color:#d1d5db;">—</span>')
    received_by_tag.short_description = 'Qabul qildi'


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display   = [
        'number_tag', 'order_tag', 'client_tag',
        'status_badge', 'signed_date', 'valid_until', 'created_at',
    ]
    list_filter    = ['status', 'signed_date', 'created_at']
    search_fields  = ['contract_number', 'order__order_number', 'order__client__name']
    ordering       = ['-created_at']
    list_per_page  = 25
    readonly_fields = ['contract_number']
    actions        = ['download_pdf', 'mark_active']

    fieldsets = (
        ('📝 Shartnoma', {
            'fields': ('contract_number', 'order', 'status', ('signed_date', 'valid_until')),
        }),
        ('📄 Matn', {
            'fields': ('terms', 'notes'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order__client')

    def number_tag(self, obj):
        return format_html(
            '<span style="font-family:monospace;font-weight:700;color:#f97316;">#{}</span>',
            obj.contract_number
        )
    number_tag.short_description = 'Raqam'

    def order_tag(self, obj):
        return format_html(
            '<span style="font-family:monospace;color:#6366f1;">#{}</span>',
            obj.order.order_number
        )
    order_tag.short_description = 'Buyurtma'

    def client_tag(self, obj):
        return format_html(
            '<strong style="color:#111;">{}</strong>',
            obj.order.client.name
        )
    client_tag.short_description = 'Mijoz'

    def status_badge(self, obj):
        styles = {
            'draft':     ('#6b7280', '#f3f4f6', '📝 Qoralama'),
            'active':    ('#1d4ed8', '#dbeafe', '✅ Faol'),
            'done':      ('#065f46', '#d1fae5', '🏁 Bajarildi'),
            'cancelled': ('#991b1b', '#fee2e2', '❌ Bekor'),
        }
        color, bg, label = styles.get(obj.status, ('#374151', '#f3f4f6', obj.get_status_display()))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:20px;'
            'font-size:11px;font-weight:700;">{}</span>',
            bg, color, label
        )
    status_badge.short_description = 'Holat'

    @admin.action(description='📥 PDF yuklab olish')
    def download_pdf(self, request, queryset):
        if queryset.count() == 1:
            contract = queryset.first()
            try:
                pdf  = contract.generate_pdf()
                resp = HttpResponse(pdf, content_type='application/pdf')
                resp['Content-Disposition'] = (
                    f'attachment; filename="shartnoma_{contract.contract_number}.pdf"'
                )
                return resp
            except Exception as e:
                self.message_user(request, f'PDF xatosi: {e}', level='error')
        else:
            self.message_user(request, 'Faqat bitta shartnoma tanlang!', level='warning')

    @admin.action(description='✅ Faol deb belgilash')
    def mark_active(self, request, queryset):
        count = queryset.update(status='active')
        self.message_user(request, f'{count} ta shartnoma faollashtirildi.')