from django import forms
from django.contrib import admin
from django.contrib.admin import display
from django.db.models import Count, Sum
from django.utils.html import format_html, mark_safe
from .models import Client


# ── Telefon input mask formasi ───────────────────────────────────────────────
class ClientAdminForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = '__all__'
        widgets = {
            'phone':  forms.TextInput(attrs={
                'placeholder': '+998(90) 123-45-67',
                'style': 'font-family: monospace; letter-spacing: 1px;',
            }),
            'phone2': forms.TextInput(attrs={
                'placeholder': '+998(90) 123-45-67',
                'style': 'font-family: monospace; letter-spacing: 1px;',
            }),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        import re
        if phone and not re.match(r'^\+998\(\d{2}\) \d{3}-\d{2}-\d{2}$', phone):
            raise forms.ValidationError("Format: +998(90) 123-45-67")
        return phone

    def clean_phone2(self):
        phone2 = self.cleaned_data.get('phone2', '').strip()
        import re
        if phone2 and not re.match(r'^\+998\(\d{2}\) \d{3}-\d{2}-\d{2}$', phone2):
            raise forms.ValidationError("Format: +998(90) 123-45-67")
        return phone2


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    form = ClientAdminForm

    list_display       = ['avatar_tag', 'name_tag', 'phone_tag', 'location_tag', 'orders_tag', 'spent_tag', 'is_archived_tag', 'created_at']
    list_display_links = ['avatar_tag', 'name_tag']
    list_filter        = ['is_archived', 'region', 'created_at']
    search_fields      = ['name', 'phone', 'phone2', 'email', 'city', 'region']
    ordering           = ['-created_at']
    date_hierarchy     = 'created_at'
    list_per_page      = 25
    actions            = ['archive_clients', 'unarchive_clients']

    # Jazzmin horizontal_tabs uchun fieldsetlar
    fieldsets = (
        ("👤 Mijoz", {
            'fields': ('name', ('phone', 'phone2'), 'email', 'avatar', 'notes'),
        }),
        ('📍 Manzil', {
            'fields': (('region', 'district'), ('mfy', 'city'), 'address'),
        }),
        ('📁 Arxiv', {
            'fields': ('is_archived', 'archived_at', 'archived_name', 'archived_phone'),
            'classes': ('collapse',),
        }),
    )
    readonly_fields = ['archived_at', 'archived_name', 'archived_phone', 'created_at']

    class Media:
        js = ('admin/js/phone_mask.js',)

    def get_queryset(self, request):
        # Annotate qilib N+1 muammosini hal qilamiz
        return (
            super().get_queryset(request)
            .annotate(
                _order_count=Count('orders', distinct=True),
                _total_spent_calc=Sum('orders__total_amount'),
            )
        )

    @display(description='')
    def avatar_tag(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:38px;height:38px;border-radius:50%;'
                'object-fit:cover;border:2px solid #e5e7eb;">',
                obj.avatar.url
            )
        initials = obj.name[:2].upper() if obj.name else '??'
        bg_colors  = ['#dbeafe', '#fce7f3', '#dcfce7', '#fef9c3', '#ede9fe']
        txt_colors = ['#1d4ed8', '#9d174d', '#166534', '#854d0e', '#5b21b6']
        idx = hash(obj.name) % 5
        return format_html(
            '<div style="width:38px;height:38px;border-radius:50%;background:{};'
            'display:flex;align-items:center;justify-content:center;'
            'font-weight:700;font-size:13px;color:{};">{}</div>',
            bg_colors[idx], txt_colors[idx], initials
        )

    @display(description='Mijoz', ordering='name')
    def name_tag(self, obj):
        return format_html('<strong style="color:#111;font-size:13px;">{}</strong>', obj.name)

    @display(description='Telefon', ordering='phone')
    def phone_tag(self, obj):
        if obj.phone2:
            return format_html(
                '<span style="color:#374151;font-family:monospace;">📞 {}</span>'
                '<br>'
                '<span style="color:#9ca3af;font-size:11px;font-family:monospace;">📞 {}</span>',
                obj.phone, obj.phone2,
            )
        return format_html(
            '<span style="color:#374151;font-family:monospace;">📞 {}</span>',
            obj.phone,
        )

    @display(description='Joylashuv')
    def location_tag(self, obj):
        parts = [p for p in [obj.city, obj.region] if p]
        if parts:
            return format_html('<span style="color:#6b7280;font-size:12px;">📍 {}</span>', ', '.join(parts))
        return mark_safe('<span style="color:#d1d5db;">—</span>')

    @display(description='Buyurtmalar', ordering='_order_count')
    def orders_tag(self, obj):
        # annotated field dan foydalanamiz (N+1 muammo yo'q)
        count = getattr(obj, '_order_count', 0) or 0
        if count > 0:
            return format_html(
                '<span style="background:#eff6ff;color:#1d4ed8;padding:2px 10px;'
                'border-radius:100px;font-size:12px;font-weight:700;">🛒 {} ta</span>',
                count
            )
        return mark_safe('<span style="color:#d1d5db;">0</span>')

    @display(description='Xaridlar', ordering='_total_spent_calc')
    def spent_tag(self, obj):
        # annotated aggregation dan foydalanamiz
        total = getattr(obj, '_total_spent_calc', None) or 0
        if total > 0:
            # MUHIM: format_html ichida {:,.0f} SafeString'ga ishlamaydi,
            # shuning uchun avval string'ga o'giramiz
            formatted = '{:,.0f}'.format(float(total))
            return format_html(
                '<span style="color:#059669;font-weight:700;">{} so\'m</span>',
                formatted
            )
        return mark_safe('<span style="color:#d1d5db;">0</span>')

    @display(description='Holat', ordering='is_archived')
    def is_archived_tag(self, obj):
        if obj.is_archived:
            return mark_safe(
                '<span style="background:#f3f4f6;color:#6b7280;padding:2px 8px;'
                'border-radius:100px;font-size:11px;font-weight:700;">📁 Arxiv</span>'
            )
        return mark_safe(
            '<span style="background:#d1fae5;color:#065f46;padding:2px 8px;'
            'border-radius:100px;font-size:11px;font-weight:700;">✓ Faol</span>'
        )

    @admin.action(description='📁 Arxivlash')
    def archive_clients(self, request, queryset):
        count = 0
        for client in queryset.filter(is_archived=False):
            client.archive()
            count += 1
        self.message_user(request, f'{count} ta mijoz arxivlandi.')

    @admin.action(description='✓ Arxivdan chiqarish')
    def unarchive_clients(self, request, queryset):
        count = queryset.filter(is_archived=True).update(
            is_archived=False,
            archived_at=None,
            archived_name='',
            archived_phone='',
        )
        self.message_user(request, f'{count} ta mijoz arxivdan chiqarildi.')