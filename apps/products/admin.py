from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.db.models import Count
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display        = ['name_tag', 'slug', 'product_count_tag', 'description_short', 'created_at']
    list_display_links  = ['name_tag']
    search_fields       = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering            = ['name']
    list_per_page       = 20

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_pc=Count('products'))

    def name_tag(self, obj):
        return format_html(
            '<strong style="color:#111;font-size:13px;">{}</strong>', obj.name
        )
    name_tag.short_description = 'Kategoriya'
    name_tag.admin_order_field = 'name'

    def product_count_tag(self, obj):
        count = getattr(obj, '_pc', 0)
        color = '#059669' if count > 0 else '#9ca3af'
        bg    = '#f0fdf4' if count > 0 else '#f9fafb'
        return format_html(
            '<span style="background:{};color:{};padding:3px 12px;'
            'border-radius:20px;font-size:12px;font-weight:700;">📦 {} ta</span>',
            bg, color, count
        )
    product_count_tag.short_description = 'Mahsulotlar soni'
    product_count_tag.admin_order_field = '_pc'

    def description_short(self, obj):
        if obj.description:
            text = obj.description[:60] + ('...' if len(obj.description) > 60 else '')
            return format_html('<span style="color:#6b7280;font-size:12px;">{}</span>', text)
        return mark_safe('<span style="color:#d1d5db;">—</span>')
    description_short.short_description = 'Tavsif'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display       = [
        'image_tag', 'name_tag', 'barcode_tag', 'sku_tag',
        'category_tag', 'price_tag', 'cost_tag',
        'margin_tag', 'stock_tag', 'active_tag',
    ]
    list_display_links = ['image_tag', 'name_tag']
    list_filter        = ['is_active', 'category', 'created_at']
    search_fields      = ['name', 'sku', 'barcode', 'material', 'color']
    ordering           = ['name']
    list_per_page      = 25
    actions            = ['make_active', 'make_inactive', 'print_barcodes']

    fieldsets = (
        ("📦 Asosiy ma'lumotlar", {
            'fields': ('name', ('sku', 'barcode'), 'category', 'description', 'is_active'),
        }),
        ('🖼 Rasm', {
            'fields': ('image',),
        }),
        ('💰 Narxlar', {
            'fields': (('cost_price', 'selling_price'),),
        }),
        ('🛋 Xususiyatlar', {
            'fields': (('material', 'color', 'dimensions'),),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')

    # ── Actions ──────────────────────────────────────────────────────

    @admin.action(description='✅ Tanlangan mahsulotlarni faollashtirish')
    def make_active(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} ta mahsulot faollashtirildi.')

    @admin.action(description='❌ Tanlangan mahsulotlarni nofaol qilish')
    def make_inactive(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} ta mahsulot nofaol qilindi.')

    @admin.action(description='🔲 Barcode chop etish (PDF)')
    def print_barcodes(self, request, queryset):
        from django.http import HttpResponse
        import io
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import cm
            from reportlab.lib.enums import TA_CENTER
            from reportlab.graphics.barcode import code128
            from reportlab.graphics.shapes import Drawing
        except ImportError:
            self.message_user(request, 'pip install reportlab', level='error')
            return

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4,
                                rightMargin=1*cm, leftMargin=1*cm,
                                topMargin=1*cm, bottomMargin=1*cm)
        story = []
        S = lambda **kw: ParagraphStyle('s', **kw)
        cells = []

        for product in queryset:
            bc_val = product.barcode or product.sku
            try:
                bc = code128.Code128(bc_val, barHeight=1.4*cm, barWidth=0.8)
            except Exception:
                bc = None

            cell_content = []
            if bc:
                d = Drawing(5*cm, 1.8*cm)
                d.add(bc)
                cell_content.append(d)
            cell_content.append(
                Paragraph(
                    f'<b>{product.name[:22]}</b>',
                    S(fontSize=7, alignment=TA_CENTER, fontName='Helvetica-Bold')
                )
            )
            cell_content.append(
                Paragraph(
                    f'{bc_val}',
                    S(fontSize=7, alignment=TA_CENTER, textColor=colors.HexColor('#374151'))
                )
            )
            cell_content.append(
                Paragraph(
                    f'{product.selling_price:,.0f} so\'m',
                    S(fontSize=8, alignment=TA_CENTER, fontName='Helvetica-Bold',
                      textColor=colors.HexColor('#f97316'))
                )
            )
            cells.append(cell_content)

        # 3 ta ustunli jadval
        rows = [cells[i:i+3] for i in range(0, len(cells), 3)]
        for row in rows:
            while len(row) < 3:
                row.append([''])
            t = Table([row], colWidths=[6*cm, 6*cm, 6*cm])
            t.setStyle(TableStyle([
                ('BOX',         (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('INNERGRID',   (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('ALIGN',       (0,0), (-1,-1), 'CENTER'),
                ('VALIGN',      (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING',  (0,0), (-1,-1), 6),
                ('BOTTOMPADDING',(0,0),(-1,-1), 6),
            ]))
            story.append(t)
            story.append(Spacer(1, 0.2*cm))

        doc.build(story)
        resp = HttpResponse(buf.getvalue(), content_type='application/pdf')
        resp['Content-Disposition'] = 'attachment; filename="barcodes.pdf"'
        return resp

    # ── Columns ──────────────────────────────────────────────────────

    def image_tag(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:46px;height:46px;border-radius:8px;'
                'object-fit:cover;border:2px solid #e5e7eb;">',
                obj.image.url
            )
        return format_html(
            '<div style="width:46px;height:46px;border-radius:8px;background:#f3f4f6;'
            'display:flex;align-items:center;justify-content:center;'
            'font-size:20px;border:1px solid #e2e8f0;">🪑</div>'
        )
    image_tag.short_description = ''

    def name_tag(self, obj):
        parts = [p for p in [obj.material, obj.color] if p]
        sub   = ' · '.join(parts)
        if sub:
            return format_html(
                '<div style="line-height:1.3;">'
                '<strong style="color:#111;">{}</strong><br>'
                '<span style="font-size:11px;color:#6b7280;">{}</span>'
                '</div>',
                obj.name, sub
            )
        return format_html('<strong style="color:#111;">{}</strong>', obj.name)
    name_tag.short_description = 'Mahsulot nomi'
    name_tag.admin_order_field = 'name'

    def barcode_tag(self, obj):
        val = obj.barcode or '—'
        if obj.barcode:
            return format_html(
                '<code style="background:#fef3c7;padding:2px 6px;border-radius:4px;'
                'font-size:11px;color:#92400e;">🔲 {}</code>',
                val
            )
        return format_html(
            '<code style="background:#f3f4f6;padding:2px 6px;border-radius:4px;'
            'font-size:11px;color:#9ca3af;">{}</code>',
            val
        )
    barcode_tag.short_description = 'Barcode'

    def sku_tag(self, obj):
        return format_html(
            '<code style="background:#f3f4f6;padding:2px 6px;border-radius:4px;'
            'font-size:11px;color:#374151;">{}</code>',
            obj.sku or '—'
        )
    sku_tag.short_description = 'SKU'
    sku_tag.admin_order_field = 'sku'

    def category_tag(self, obj):
        if obj.category:
            return format_html(
                '<span style="background:#eff6ff;color:#1d4ed8;padding:2px 8px;'
                'border-radius:6px;font-size:12px;font-weight:600;">{}</span>',
                obj.category.name
            )
        return mark_safe('<span style="color:#d1d5db;">—</span>')
    category_tag.short_description = 'Kategoriya'

    def price_tag(self, obj):
        price = '{:,.0f}'.format(float(obj.selling_price))
        return format_html(
            '<strong style="color:#059669;">{} so\'m</strong>',
            price
        )
    price_tag.short_description = 'Sotish narxi'
    price_tag.admin_order_field = 'selling_price'

    def cost_tag(self, obj):
        cost = '{:,.0f}'.format(float(obj.cost_price))
        return format_html(
            '<span style="color:#6b7280;font-size:12px;">{} so\'m</span>',
            cost
        )
    cost_tag.short_description = 'Tan narxi'

    def margin_tag(self, obj):
        margin = obj.margin_percent
        if margin > 0:
            color = '#059669' if margin >= 20 else '#f59e0b' if margin >= 10 else '#dc2626'
            margin_str = '{:.1f}'.format(margin)
            return format_html(
                '<span style="color:{};font-weight:700;">{}%</span>',
                color, margin_str
            )
        return mark_safe('<span style="color:#d1d5db;">—</span>')
    margin_tag.short_description = 'Margin'

    def stock_tag(self, obj):
        qty = obj.stock_quantity or 0
        if qty <= 0:
            return mark_safe(
                '<span style="background:#fee2e2;color:#991b1b;padding:3px 10px;'
                'border-radius:20px;font-size:11px;font-weight:700;">🔴 Tugagan</span>'
            )
        try:
            min_q = obj.stock.min_quantity
        except Exception:
            min_q = 5
        if qty <= min_q:
            return format_html(
                '<span style="background:#fef3c7;color:#92400e;padding:3px 10px;'
                'border-radius:20px;font-size:11px;font-weight:700;">🟡 {} ta</span>', qty
            )
        return format_html(
            '<span style="background:#d1fae5;color:#065f46;padding:3px 10px;'
            'border-radius:20px;font-size:11px;font-weight:700;">🟢 {} ta</span>', qty
        )
    stock_tag.short_description = 'Stok'

    def active_tag(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span style="background:#d1fae5;color:#065f46;padding:3px 10px;'
                'border-radius:20px;font-size:11px;font-weight:700;">✓ Faol</span>'
            )
        return mark_safe(
            '<span style="background:#f3f4f6;color:#9ca3af;padding:3px 10px;'
            'border-radius:20px;font-size:11px;">✗ Nofaol</span>'
        )
    active_tag.short_description = 'Holat'
    active_tag.admin_order_field = 'is_active'