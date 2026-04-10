from django.contrib import admin
from django.contrib.admin import display
from django.utils.html import format_html, mark_safe
from .models import BotSession, PaymeTransaction, ClickTransaction, ScheduledMessage


# ── BotSession Admin ───────────────────────────────────────────────────────────
@admin.register(BotSession)
class BotSessionAdmin(admin.ModelAdmin):
    list_display   = ['chat_id_tag', 'step_tag', 'lang_tag', 'cart_items_tag', 'updated_at']
    list_filter    = ['lang', 'updated_at']
    search_fields  = ['chat_id', 'step']
    ordering       = ['-updated_at']
    list_per_page  = 30
    readonly_fields = ['chat_id', 'updated_at', 'data']

    fieldsets = (
        ('📱 Sessiya', {
            'fields': ('chat_id', 'lang', 'step', 'data', 'updated_at'),
        }),
    )

    @display(description='Chat ID', ordering='chat_id')
    def chat_id_tag(self, obj):
        return format_html(
            '<code style="background:#eff6ff;color:#1d4ed8;padding:2px 8px;'
            'border-radius:4px;font-size:12px;font-weight:700;">🆔 {}</code>',
            obj.chat_id
        )

    @display(description='Qadam', ordering='step')
    def step_tag(self, obj):
        if obj.step:
            return format_html(
                '<code style="background:#f3f4f6;color:#374151;padding:2px 6px;'
                'border-radius:4px;font-size:11px;">{}</code>',
                obj.step
            )
        return mark_safe('<span style="color:#d1d5db;">—</span>')

    @display(description='Til', ordering='lang')
    def lang_tag(self, obj):
        flags = {'uz': '🇺🇿 UZ', 'ru': '🇷🇺 RU', 'en': '🇬🇧 EN'}
        return format_html(
            '<span style="font-size:13px;font-weight:600;color:#374151;">{}</span>',
            flags.get(obj.lang, obj.lang.upper())
        )

    @display(description='Savat')
    def cart_items_tag(self, obj):
        cart = obj.data.get('cart', []) if isinstance(obj.data, dict) else []
        if cart:
            total_qty = sum(item.get('qty', 0) for item in cart)
            return format_html(
                '<span style="background:#d1fae5;color:#065f46;padding:2px 8px;'
                'border-radius:20px;font-size:11px;font-weight:700;">🛒 {} dona</span>',
                total_qty
            )
        return mark_safe('<span style="color:#d1d5db;">Bo\'sh</span>')


# ── PaymeTransaction Admin ────────────────────────────────────────────────────
PAYMENT_STATUS_STYLES = {
    'pending':   ('#92400e', '#fef3c7', '⏳ Kutilmoqda'),
    'paid':      ('#065f46', '#d1fae5', '✅ To\'langan'),
    'cancelled': ('#991b1b', '#fee2e2', '❌ Bekor'),
    'error':     ('#7f1d1d', '#fee2e2', '⚠️ Xato'),
}


@admin.register(PaymeTransaction)
class PaymeTransactionAdmin(admin.ModelAdmin):
    list_display   = ['payme_id_tag', 'order_tag', 'amount_tag', 'status_badge', 'chat_id_tag', 'created_at']
    list_filter    = ['status', 'created_at']
    search_fields  = ['payme_id', 'order__order_number', 'chat_id']
    ordering       = ['-created_at']
    date_hierarchy = 'created_at'
    list_per_page  = 30
    readonly_fields = ['created_at', 'updated_at', 'payme_id', 'create_time', 'perform_time', 'cancel_time']

    fieldsets = (
        ('💳 Payme tranzaksiya', {
            'fields': ('order', 'amount', 'status', 'payme_id', 'chat_id'),
        }),
        ('⏱️ Vaqtlar', {
            'fields': ('create_time', 'perform_time', 'cancel_time', 'reason', 'created_at'),
            'classes': ('collapse',),
        }),
        ('🗂️ Qo\'shimcha', {
            'fields': ('extra',),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order__client')

    @display(description='Payme ID')
    def payme_id_tag(self, obj):
        val = obj.payme_id or f'#{obj.pk}'
        return format_html(
            '<code style="background:#f3f4f6;color:#374151;padding:2px 6px;'
            'border-radius:4px;font-size:11px;">{}</code>',
            val
        )

    @display(description='Buyurtma')
    def order_tag(self, obj):
        return format_html(
            '<span style="font-family:monospace;color:#f97316;font-weight:700;">#{}</span>',
            obj.order.order_number
        )

    @display(description='Summa', ordering='amount')
    def amount_tag(self, obj):
        amount = '{:,.0f}'.format(float(obj.amount))
        return format_html(
            '<strong style="color:#059669;">{} so\'m</strong>',
            amount
        )

    @display(description='Holat', ordering='status')
    def status_badge(self, obj):
        color, bg, label = PAYMENT_STATUS_STYLES.get(obj.status, ('#374151', '#f3f4f6', obj.status))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:20px;'
            'font-size:11px;font-weight:700;">{}</span>',
            bg, color, label
        )

    @display(description='Telegram')
    def chat_id_tag(self, obj):
        if obj.chat_id:
            return format_html(
                '<code style="font-size:11px;color:#6b7280;">{}</code>',
                obj.chat_id
            )
        return mark_safe('<span style="color:#d1d5db;">—</span>')


# ── ClickTransaction Admin ────────────────────────────────────────────────────
@admin.register(ClickTransaction)
class ClickTransactionAdmin(admin.ModelAdmin):
    list_display   = ['click_id_tag', 'order_tag', 'amount_tag', 'status_badge', 'created_at']
    list_filter    = ['status', 'created_at']
    search_fields  = ['click_trans_id', 'order__order_number', 'chat_id']
    ordering       = ['-created_at']
    date_hierarchy = 'created_at'
    list_per_page  = 30
    readonly_fields = ['created_at', 'updated_at', 'click_trans_id']

    fieldsets = (
        ('💳 Click tranzaksiya', {
            'fields': ('order', 'amount', 'status', 'click_trans_id', 'merchant_trans_id', 'chat_id'),
        }),
        ('🗂️ Qo\'shimcha', {
            'fields': ('extra', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order__client')

    @display(description='Click ID')
    def click_id_tag(self, obj):
        val = obj.click_trans_id or f'#{obj.pk}'
        return format_html(
            '<code style="background:#eff6ff;color:#1d4ed8;padding:2px 6px;'
            'border-radius:4px;font-size:11px;">{}</code>',
            val
        )

    @display(description='Buyurtma')
    def order_tag(self, obj):
        return format_html(
            '<span style="font-family:monospace;color:#f97316;font-weight:700;">#{}</span>',
            obj.order.order_number
        )

    @display(description='Summa', ordering='amount')
    def amount_tag(self, obj):
        amount = '{:,.0f}'.format(float(obj.amount))
        return format_html(
            '<strong style="color:#059669;">{} so\'m</strong>',
            amount
        )

    @display(description='Holat', ordering='status')
    def status_badge(self, obj):
        color, bg, label = PAYMENT_STATUS_STYLES.get(obj.status, ('#374151', '#f3f4f6', obj.status))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:20px;'
            'font-size:11px;font-weight:700;">{}</span>',
            bg, color, label
        )


# ── ScheduledMessage Admin ────────────────────────────────────────────────────
MSG_TYPE_ICONS = {
    'delivery_reminder': '🚚',
    'payment_reminder':  '💰',
    'order_status':      '📦',
    'daily_report':      '📊',
    'low_stock':         '⚠️',
    'custom':            '✉️',
}


@admin.register(ScheduledMessage)
class ScheduledMessageAdmin(admin.ModelAdmin):
    list_display   = ['type_tag', 'chat_id_tag', 'text_short', 'send_at', 'sent_tag', 'order_tag']
    list_filter    = ['msg_type', 'sent', 'send_at']
    search_fields  = ['chat_id', 'text', 'order__order_number']
    ordering       = ['send_at']
    date_hierarchy = 'send_at'
    list_per_page  = 30
    readonly_fields = ['created_at', 'updated_at', 'sent_at']

    fieldsets = (
        ('📨 Xabar', {
            'fields': ('chat_id', 'msg_type', 'text', 'buttons', 'order'),
        }),
        ('⏰ Yuborish', {
            'fields': ('send_at', 'sent', 'sent_at', 'created_at'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order')

    @display(description='Tur', ordering='msg_type')
    def type_tag(self, obj):
        icon = MSG_TYPE_ICONS.get(obj.msg_type, '✉️')
        return format_html(
            '<span style="background:#f3f4f6;color:#374151;padding:2px 10px;'
            'border-radius:20px;font-size:11px;font-weight:600;">{} {}</span>',
            icon, obj.get_msg_type_display()
        )

    @display(description='Chat ID')
    def chat_id_tag(self, obj):
        return format_html(
            '<code style="font-size:11px;color:#6b7280;">{}</code>',
            obj.chat_id
        )

    @display(description='Xabar')
    def text_short(self, obj):
        short = obj.text[:60] + ('...' if len(obj.text) > 60 else '')
        return format_html('<span style="color:#374151;font-size:12px;">{}</span>', short)

    @display(description='Yuborildi', ordering='sent')
    def sent_tag(self, obj):
        if obj.sent:
            return mark_safe(
                '<span style="background:#d1fae5;color:#065f46;padding:2px 8px;'
                'border-radius:20px;font-size:11px;font-weight:700;">✓ Ha</span>'
            )
        return mark_safe(
            '<span style="background:#fef3c7;color:#92400e;padding:2px 8px;'
            'border-radius:20px;font-size:11px;font-weight:700;">⏳ Yo\'q</span>'
        )

    @display(description='Buyurtma')
    def order_tag(self, obj):
        if obj.order:
            return format_html(
                '<span style="font-family:monospace;color:#f97316;font-weight:700;">#{}</span>',
                obj.order.order_number
            )
        return mark_safe('<span style="color:#d1d5db;">—</span>')
