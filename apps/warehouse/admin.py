from django.contrib import admin
from django.contrib.admin import display
from django.utils.html import format_html, mark_safe
from .models import Stock, StockMovement


# ── Stock Admin ───────────────────────────────────────────────────────────────
@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = [
        'product_tag', 'category_tag',
        'quantity_bar', 'min_quantity_tag',
        'status_tag', 'updated_at',
    ]
    list_filter = [
        ('product__category', admin.RelatedOnlyFieldListFilter),
        'updated_at',
    ]
    search_fields = ['product__name', 'product__sku']
    ordering = ['product__name']
    list_per_page = 30

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product__category')

    @display(description='Mahsulot', ordering='product__name')
    def product_tag(self, obj):
        return format_html(
            '<div style="line-height:1.4;">'
            '<strong style="color:#111;">{}</strong><br>'
            '<code style="background:#f3f4f6;padding:1px 6px;border-radius:4px;'
            'font-size:11px;color:#6b7280;">{}</code>'
            '</div>',
            obj.product.name, obj.product.sku
        )

    @display(description='Kategoriya')
    def category_tag(self, obj):
        if obj.product.category:
            return format_html(
                '<span style="background:#eff6ff;color:#1d4ed8;padding:2px 8px;'
                'border-radius:6px;font-size:11px;font-weight:600;">{}</span>',
                obj.product.category.name
            )
        return mark_safe('<span style="color:#d1d5db;">—</span>')

    @display(description='Miqdor (progress)', ordering='quantity')
    def quantity_bar(self, obj):
        qty = max(obj.quantity, 0)
        min_q = obj.min_quantity
        max_vis = max(min_q * 3, qty + 1, 1)
        pct = min(int(qty / max_vis * 100), 100)

        if qty <= 0:
            color, bg = '#dc2626', '#fee2e2'
        elif qty <= min_q:
            color, bg = '#d97706', '#fef3c7'
        else:
            color, bg = '#059669', '#d1fae5'

        # 🟢 TUZATILDI: Miqdorni tashqarida formatlaymiz
        formatted_qty = "{:,.0f}".format(qty)

        return format_html(
            '<div style="min-width:120px;">'
            '<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
            '<strong style="color:{};">{} dona</strong>'
            '</div>'
            '<div style="height:6px;background:#f3f4f6;border-radius:3px;overflow:hidden;">'
            '<div style="height:100%;width:{}%;background:{};border-radius:3px;'
            'transition:width 0.3s;"></div>'
            '</div>'
            '</div>',
            color, formatted_qty, pct, color
        )

    @display(description='Min. chegara', ordering='min_quantity')
    def min_quantity_tag(self, obj):
        # 🟢 TUZATILDI: Miqdorni tashqarida formatlaymiz
        formatted_min = "{:,.0f}".format(obj.min_quantity)
        return format_html(
            '<span style="color:#6b7280;font-size:12px;">⚠ {} dona</span>',
            formatted_min
        )

    @display(description='Holat', ordering='quantity')
    def status_tag(self, obj):
        qty = obj.quantity
        if qty <= 0:
            return mark_safe('<span style="background:#fee2e2;color:#991b1b;padding:3px 10px;'
                             'border-radius:100px;font-size:11px;font-weight:700;">🔴 Tugagan</span>'
                             )
        elif obj.is_low:
            return mark_safe('<span style="background:#fef3c7;color:#92400e;padding:3px 10px;'
                             'border-radius:100px;font-size:11px;font-weight:700;">🟡 Kam qoldi</span>'
                             )
        return mark_safe('<span style="background:#d1fae5;color:#065f46;padding:3px 10px;'
                         'border-radius:100px;font-size:11px;font-weight:700;">🟢 Yetarli</span>'
                         )


# ── StockMovement Admin ───────────────────────────────────────────────────────
MOVE_STYLES = {
    'in': ('#065f46', '#d1fae5', '📥 Kirim'),
    'out': ('#991b1b', '#fee2e2', '📤 Chiqim'),
    'adjust': ('#1d4ed8', '#dbeafe', '🔧 Tuzatish'),
}


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        'product_tag', 'type_badge',
        'quantity_tag', 'reason_tag',
        'performed_by_tag', 'created_at',
    ]
    list_filter = [
        'movement_type',
        ('product__category', admin.RelatedOnlyFieldListFilter),
        'created_at',
    ]
    search_fields = ['product__name', 'product__sku', 'reason']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'
    list_per_page = 30
    readonly_fields = ['created_at']

    fieldsets = (
        ("Harakat ma'lumotlari", {
            'fields': ('product', 'movement_type', 'quantity', 'reason', 'performed_by'),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product__category', 'performed_by')

    @display(description='Mahsulot', ordering='product__name')
    def product_tag(self, obj):
        return format_html(
            '<div><strong style="color:#111;">{}</strong><br>'
            '<code style="background:#f3f4f6;padding:1px 5px;border-radius:4px;'
            'font-size:11px;color:#6b7280;">{}</code></div>',
            obj.product.name, obj.product.sku
        )

    @display(description='Harakat turi', ordering='movement_type')
    def type_badge(self, obj):
        color, bg, label = MOVE_STYLES.get(obj.movement_type, ('#374151', '#f3f4f6', '?'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:100px;'
            'font-size:11px;font-weight:700;">{}</span>',
            bg, color, label
        )

    @display(description='Miqdor', ordering='quantity')
    def quantity_tag(self, obj):
        if obj.movement_type == 'in':
            color, prefix = '#059669', '+'
        elif obj.movement_type == 'out':
            color, prefix = '#dc2626', '-'
        else:
            color, prefix = '#2563eb', '='

        # 🟢 TUZATILDI: Miqdorni tashqarida formatlaymiz
        formatted_val = "{:,.0f}".format(obj.quantity)

        return format_html(
            '<span style="font-weight:800;font-size:15px;color:{};">{}{}</span>',
            color, prefix, formatted_val
        )

    @display(description='Sabab')
    def reason_tag(self, obj):
        if obj.reason:
            return format_html('<span style="color:#374151;">{}</span>', obj.reason)
        return mark_safe('<span style="color:#d1d5db;">—</span>')

    @display(description='Kim tomonidan', ordering='performed_by__username')
    def performed_by_tag(self, obj):
        if obj.performed_by:
            name = obj.performed_by.get_full_name() or obj.performed_by.username
            return format_html('<span style="color:#374151;">👤 {}</span>', name)
        return mark_safe('<span style="color:#d1d5db;">—</span>')