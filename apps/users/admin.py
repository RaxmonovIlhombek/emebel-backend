from django import forms
from django.contrib import admin
from django.contrib.admin import display
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils.html import format_html, mark_safe
from .models import User, Message

# ── RANG VA BELGILAR ────────────────────────────────────────────────────────
ROLE_COLORS = {
    'admin':      ('#dc2626', '#fef2f2'),
    'manager':    ('#2563eb', '#eff6ff'),
    'accountant': ('#7c3aed', '#f5f3ff'),
    'worker':     ('#059669', '#ecfdf5'),
    'client':     ('#6b7280', '#f9fafb'),
}
ROLE_ICONS = {
    'admin': '👑', 'manager': '💼',
    'accountant': '📊', 'worker': '🔧', 'client': '👤',
}

# ── TELEFON WIDGET ──────────────────────────────────────────────────────────
PHONE_WIDGET = forms.TextInput(attrs={
    'placeholder': '+998(90) 123-45-67',
    'style': 'font-family: monospace; letter-spacing: 1px;',
})

# ── FORMALAR ────────────────────────────────────────────────────────────────
class CustomUserCreationForm(UserCreationForm):
    phone = forms.CharField(
        required=False,
        widget=PHONE_WIDGET,
        help_text="Format: +998(90) 123-45-67"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'phone', 'role')

    def clean_phone(self):
        import re
        phone = self.cleaned_data.get('phone', '').strip()
        if phone and not re.match(r'^\+998\(\d{2}\) \d{3}-\d{2}-\d{2}$', phone):
            raise forms.ValidationError("Format: +998(90) 123-45-67")
        return phone or None

class CustomUserChangeForm(UserChangeForm):
    phone = forms.CharField(
        required=False,
        widget=PHONE_WIDGET,
        help_text="Format: +998(90) 123-45-67"
    )

    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'

    def clean_phone(self):
        import re
        phone = self.cleaned_data.get('phone', '').strip()
        if phone and not re.match(r'^\+998\(\d{2}\) \d{3}-\d{2}-\d{2}$', phone):
            raise forms.ValidationError("Format: +998(90) 123-45-67")
        return phone or None

# ── USER ADMIN ──────────────────────────────────────────────────────────────
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form     = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display       = ['avatar_tag', 'username_link', 'full_name', 'role_badge', 'phone', 'telegram_tag', 'is_active_tag', 'date_joined']
    list_display_links = ['avatar_tag', 'username_link']
    list_filter        = ['role', 'is_active', 'is_staff']
    search_fields      = ['username', 'first_name', 'last_name', 'phone', 'email']
    ordering           = ['-date_joined']
    list_per_page      = 25

    # Jazzmin tabs uchun fieldsetlar
    fieldsets = (
        ("🔐 Kirish", {'fields': ('username', 'password')}),
        ("👤 Shaxsiy", {'fields': ('first_name', 'last_name', 'email', 'phone', 'avatar')}),
        ("🎭 Huquqlar", {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ("📱 Telegram", {'fields': ('telegram_chat_id', 'telegram_username'), 'classes': ('collapse',)}),
        ("🔗 Profil", {'fields': ('client_profile',), 'classes': ('collapse',)}),
        ("📅 Sanalar", {'fields': ('last_login', 'date_joined'), 'classes': ('collapse',)}),
    )

    add_fieldsets = (
        ("Yangi foydalanuvchi", {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'phone', 'role', 'password1', 'password2'),
        }),
    )

    readonly_fields = ['last_login', 'date_joined']

    # --- Custom Columns ---
    @display(description='')
    def avatar_tag(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:36px;height:36px;border-radius:50%;'
                'object-fit:cover;border:2px solid #e5e7eb;">', obj.avatar.url
            )
        initials = (obj.first_name[:1] or obj.username[:1]).upper()
        color, bg = ROLE_COLORS.get(obj.role, ('#6b7280', '#f9fafb'))
        return format_html(
            '<div style="width:36px;height:36px;border-radius:50%;background:{};'
            'display:flex;align-items:center;justify-content:center;'
            'font-weight:700;font-size:14px;color:{};">{}</div>',
            bg, color, initials
        )

    @display(description='Foydalanuvchi', ordering='username')
    def username_link(self, obj):
        return format_html('<strong style="color:#111;">{}</strong>', obj.username)

    @display(description='Ism Familiya', ordering='first_name')
    def full_name(self, obj):
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name or mark_safe('<span style="color:#9ca3af;">—</span>')

    @display(description='Rol', ordering='role')
    def role_badge(self, obj):
        color, bg = ROLE_COLORS.get(obj.role, ('#6b7280', '#f9fafb'))
        icon  = ROLE_ICONS.get(obj.role, '👤')
        label = obj.get_role_display()
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:100px;'
            'font-size:12px;font-weight:600;white-space:nowrap;">{} {}</span>',
            bg, color, icon, label
        )

    @display(description='Telegram')
    def telegram_tag(self, obj):
        if obj.telegram_username:
            return format_html(
                '<a href="https://t.me/{}" target="_blank" style="color:#0088cc;text-decoration:none;">@{}</a>',
                obj.telegram_username, obj.telegram_username
            )
        if obj.telegram_chat_id:
            return format_html('<span style="color:#6b7280;font-size:12px;">ID: {}</span>', obj.telegram_chat_id)
        return mark_safe('<span style="color:#d1d5db;">—</span>')

    @display(description='Faol', ordering='is_active')
    def is_active_tag(self, obj):
        if obj.is_active:
            return mark_safe('<span style="background:#d1fae5;color:#065f46;padding:2px 10px;border-radius:100px;font-size:11px;font-weight:700;">✓ Faol</span>')
        return mark_safe('<span style="background:#fee2e2;color:#991b1b;padding:2px 10px;border-radius:100px;font-size:11px;font-weight:700;">✗ Nofaol</span>')

# ── MESSAGE ADMIN ───────────────────────────────────────────────────────────
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin): # Standart admin.ModelAdmin ga o'zgartirildi
    list_display    = ['id', 'sender_tag', 'arrow', 'receiver_tag', 'body_short', 'is_read_tag', 'order_ref_tag', 'created_at']
    list_filter     = ['is_read', 'is_order_notification', 'created_at']
    search_fields   = ['sender__username', 'receiver__username', 'body']
    readonly_fields = ['sender', 'receiver', 'created_at']
    date_hierarchy  = 'created_at'
    ordering        = ['-created_at']
    list_per_page   = 30

    @display(description='Yuboruvchi')
    def sender_tag(self, obj):
        color, bg = ROLE_COLORS.get(obj.sender.role, ('#6b7280', '#f9fafb'))
        name = obj.sender.get_full_name() or obj.sender.username
        return format_html('<span style="background:{};color:{};padding:2px 8px;border-radius:6px;font-size:12px;font-weight:600;">{}</span>', bg, color, name)

    @display(description='')
    def arrow(self, obj):
        return mark_safe('<span style="color:#9ca3af;">→</span>')

    @display(description='Qabul qiluvchi')
    def receiver_tag(self, obj):
        color, bg = ROLE_COLORS.get(obj.receiver.role, ('#6b7280', '#f9fafb'))
        name = obj.receiver.get_full_name() or obj.receiver.username
        return format_html('<span style="background:{};color:{};padding:2px 8px;border-radius:6px;font-size:12px;font-weight:600;">{}</span>', bg, color, name)

    @display(description='Xabar')
    def body_short(self, obj):
        text = obj.body[:60] + ('...' if len(obj.body) > 60 else '')
        return format_html('<span style="color:#374151;">{}</span>', text)

    @display(description="O'qildi", ordering='is_read')
    def is_read_tag(self, obj):
        if obj.is_read:
            return mark_safe('<span style="background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:100px;font-size:11px;font-weight:700;">✓ O\'qildi</span>')
        return mark_safe('<span style="background:#fef3c7;color:#92400e;padding:2px 8px;border-radius:100px;font-size:11px;font-weight:700;">● Yangi</span>')

    @display(description='Buyurtma')
    def order_ref_tag(self, obj):
        if obj.order_ref:
            return format_html('<span style="background:#eff6ff;color:#1d4ed8;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:600;">#{}</span>', obj.order_ref)
        return mark_safe('<span style="color:#d1d5db;">—</span>')

# ── UNREGISTER ──────────────────────────────────────────────────────────────
from django.contrib.auth.models import Group
try:
    from rest_framework.authtoken.models import Token
    admin.site.unregister(Token)
except Exception:
    pass

try:
    admin.site.unregister(Group)
except Exception:
    pass