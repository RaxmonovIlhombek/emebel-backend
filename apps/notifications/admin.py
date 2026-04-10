from django.contrib import admin
from django.contrib.admin import display
from django.utils.html import format_html, mark_safe
from .models import Notification


NOTIF_TYPE_CONFIG = {
    'new_order':     ('#1d4ed8', '#dbeafe', '🛒 Yangi buyurtma'),
    'status_change': ('#7c3aed', '#f5f3ff', '🔄 Holat'),
    'payment':       ('#059669', '#ecfdf5', "💰 To'lov"),
    'overdue':       ('#dc2626', '#fee2e2', '⚠️ Kechikkan'),
    'low_stock':     ('#d97706', '#fffbeb', '📦 Kam qoldiq'),
    'message':       ('#0891b2', '#f0f9ff', '✉️ Xabar'),
    'system':        ('#6b7280', '#f9fafb', '⚙️ Tizim'),
}


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'type_badge', 'recipient_tag', 'title_tag',
        'is_read_tag', 'object_link', 'created_at',
    ]
    list_filter  = ['notif_type', 'is_read', 'created_at']
    search_fields = ['title', 'body', 'recipient__username']
    ordering     = ['-created_at']
    date_hierarchy = 'created_at'
    list_per_page  = 30
    readonly_fields = ['created_at', 'notif_type', 'recipient', 'object_id']
    actions = ['mark_read', 'mark_unread']

    fieldsets = (
        ('📬 Bildirishnoma', {
            'fields': ('recipient', 'notif_type', 'title', 'body', 'link', 'is_read', 'object_id'),
        }),
        ('📅 Meta', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('recipient')

    @display(description='Tur', ordering='notif_type')
    def type_badge(self, obj):
        color, bg, label = NOTIF_TYPE_CONFIG.get(
            obj.notif_type, ('#6b7280', '#f9fafb', obj.get_notif_type_display())
        )
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:20px;'
            'font-size:11px;font-weight:700;white-space:nowrap;">{}</span>',
            bg, color, label
        )

    @display(description='Foydalanuvchi', ordering='recipient__username')
    def recipient_tag(self, obj):
        name = obj.recipient.get_full_name() or obj.recipient.username
        return format_html(
            '<span style="color:#374151;font-weight:500;">👤 {}</span>', name
        )

    @display(description='Sarlavha')
    def title_tag(self, obj):
        style = 'font-weight:700;color:#111;' if not obj.is_read else 'color:#6b7280;'
        body_short = obj.body[:50] + ('...' if len(obj.body) > 50 else '') if obj.body else ''
        return format_html(
            '<div style="line-height:1.4;">'
            '<span style="{}">{}</span><br>'
            '<span style="font-size:11px;color:#9ca3af;">{}</span>'
            '</div>',
            style, obj.title, body_short
        )

    @display(description="O'qildi", ordering='is_read', boolean=False)
    def is_read_tag(self, obj):
        if obj.is_read:
            return mark_safe(
                '<span style="background:#d1fae5;color:#065f46;padding:2px 10px;'
                'border-radius:20px;font-size:11px;font-weight:700;">✓ O\'qildi</span>'
            )
        return mark_safe(
            '<span style="background:#fef3c7;color:#92400e;padding:2px 10px;'
            'border-radius:20px;font-size:11px;font-weight:700;">● Yangi</span>'
        )

    @display(description='Bog\'liq')
    def object_link(self, obj):
        if obj.link:
            return format_html(
                '<a href="{}" style="color:#0062ff;font-size:11px;'
                'text-decoration:none;font-weight:600;">🔗 Ko\'rish</a>',
                obj.link
            )
        if obj.object_id:
            return format_html(
                '<span style="color:#9ca3af;font-size:11px;">ID: {}</span>',
                obj.object_id
            )
        return mark_safe('<span style="color:#d1d5db;">—</span>')

    @admin.action(description="✓ O'qildi deb belgilash")
    def mark_read(self, request, queryset):
        count = queryset.update(is_read=True)
        self.message_user(request, f'{count} ta bildirishnoma o\'qildi deb belgilandi.')

    @admin.action(description='● Yangi deb belgilash')
    def mark_unread(self, request, queryset):
        count = queryset.update(is_read=False)
        self.message_user(request, f'{count} ta bildirishnoma yangi deb belgilandi.')
