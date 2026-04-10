from django.db import models
from django.conf import settings
from datetime import date
from apps.common.models import BaseModel
from apps.clients.models import Client
from apps.products.models import Product
from decimal import Decimal, ROUND_HALF_UP


class Order(BaseModel):
    STATUS_CHOICES = [
        ('new', 'Yangi'),
        ('pending', 'Jarayonda'),
        ('production', 'Ishlab chiqarishda'),
        ('ready', 'Tayyor'),
        ('delivered', 'Yetkazildi'),
        ('completed', 'Yakunlandi'),
        ('cancelled', 'Bekor qilindi'),
    ]
    PAYMENT_STATUS = [
        ('unpaid', "To'lanmagan"),
        ('partial', "Qisman to'langan"),
        ('paid', "To'langan"),
    ]

    order_number   = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Buyurtma raqami")
    client         = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='orders', verbose_name="Mijoz")
    manager        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='managed_orders', verbose_name="Menejer")
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="Holat")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='unpaid', verbose_name="To'lov holati")
    total_amount   = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="Jami summa")
    paid_amount    = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name="To'langan summa")
    discount       = models.DecimalField(max_digits=6, decimal_places=2, default=0, verbose_name="Chegirma (%)")

    delivery_region   = models.CharField(max_length=100, blank=True, verbose_name="Viloyat")
    delivery_district = models.CharField(max_length=100, blank=True, verbose_name="Tuman")
    delivery_mfy      = models.CharField(max_length=100, blank=True, verbose_name="MFY")
    delivery_address  = models.TextField(blank=True, verbose_name="Ko'cha / uy")

    delivery_date = models.DateField(null=True, blank=True, verbose_name="Yetkazish sanasi")
    notes         = models.TextField(blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name = "Buyurtma"
        verbose_name_plural = "Buyurtmalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.order_number} - {self.client.name}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            from django.utils import timezone
            self.order_number = f"MB{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)

    @property
    def full_delivery_address(self):
        parts = [self.delivery_region, self.delivery_district, self.delivery_mfy, self.delivery_address]
        return ", ".join(p for p in parts if p)

    @property
    def remaining_amount(self):
        val = self.total_amount - self.paid_amount
        return max(val, Decimal('0'))

    def get_status_badge(self):
        return {'new':'primary','pending':'info','production':'warning',
                'ready':'success','delivered':'success','completed':'dark','cancelled':'danger'}.get(self.status,'secondary')


class OrderItem(models.Model):
    order    = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name="Buyurtma")
    product  = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Mahsulot")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Miqdor")
    price    = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Narx")
    notes    = models.CharField(max_length=200, blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name = "Buyurtma elementi"
        verbose_name_plural = "Buyurtma elementlari"

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def subtotal(self):
        return self.price * self.quantity


class Payment(models.Model):
    """To'lov tarixi"""
    METHOD_CHOICES = [
        ('cash',     'Naqd'),
        ('card',     'Karta'),
        ('transfer', "Bank o'tkazma"),
        ('click',    'Click'),
        ('payme',    'Payme'),
        ('other',    'Boshqa'),
    ]
    order       = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments', verbose_name="Buyurtma")
    amount      = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Summa")
    method      = models.CharField(max_length=20, choices=METHOD_CHOICES, default='cash', verbose_name="To'lov turi")
    note        = models.CharField(max_length=200, blank=True, verbose_name="Izoh")
    external_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tashqi ID (Click/Payme)")
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='received_payments', verbose_name="Qabul qildi")
    is_confirmed = models.BooleanField(default=False, verbose_name="Tasdiqlangan")
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='submitted_payments', verbose_name="Yubordi")
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name="Sana")

    class Meta:
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"
        ordering = ['-created_at']

    def __str__(self):
        # ✅ TUZATILDI: avvalgi kodda keyingi faylning kodi shu yerga yopishib qolgan edi
        return f"#{self.order.order_number} — {self.amount:,.0f} so'm ({self.get_method_display()})"


class Expense(BaseModel):
    """Xarajatlar — ijara, oylik, xomashyo va h.k."""
    CATEGORY_CHOICES = [
        ('salary',    'Oylik (Ish haqi)'),
        ('rent',      'Ijara'),
        ('materials', 'Xomashyo (Materiallar)'),
        ('marketing', 'Reklama / Marketing'),
        ('transport', 'Logistika / Transport'),
        ('utilities', 'Kommunal to\'lovlar (Gaz, Svet)'),
        ('other',     'Boshqa xarajatlar'),
    ]

    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other', verbose_name="Kategoriya")
    amount       = models.DecimalField(max_digits=14, decimal_places=2, verbose_name="Summa")
    date         = models.DateField(default=date.today, verbose_name="Sana")
    note         = models.TextField(blank=True, verbose_name="Izoh")
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='recorded_expenses', verbose_name="Bajaruvchi")

    class Meta:
        verbose_name = "Xarajat"
        verbose_name_plural = "Xarajatlar"
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_category_display()} — {self.amount:,.0f} so'm ({self.date})"


class Contract(BaseModel):
    """Shartnoma — buyurtma bilan bog'liq rasmiy hujjat"""
    STATUS = [
        ('draft',    'Qoralama'),
        ('active',   'Faol'),
        ('done',     'Bajarildi'),
        ('cancelled','Bekor'),
    ]

    order          = models.OneToOneField(Order, on_delete=models.CASCADE,
                                           related_name='contract', verbose_name="Buyurtma")
    contract_number= models.CharField(max_length=30, unique=True, blank=True,
                                       verbose_name="Shartnoma raqami")
    status         = models.CharField(max_length=20, choices=STATUS, default='draft',
                                       verbose_name="Holat")
    signed_date    = models.DateField(null=True, blank=True, verbose_name="Imzolangan sana")
    valid_until    = models.DateField(null=True, blank=True, verbose_name="Amal qilish muddati")
    terms          = models.TextField(blank=True, verbose_name="Shartnoma shartlari")
    notes          = models.TextField(blank=True, verbose_name="Izoh")

    class Meta:
        verbose_name        = "Shartnoma"
        verbose_name_plural = "Shartnomalar"
        ordering            = ['-created_at']

    def __str__(self):
        return f"Shartnoma #{self.contract_number} — {self.order.order_number}"

    def save(self, *args, **kwargs):
        if not self.contract_number:
            from django.utils import timezone
            self.contract_number = f"SH-{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)

    def generate_pdf(self):
        """PDF shartnoma generatsiya qiladi"""
        from .contract_pdf import generate_contract_pdf
        return generate_contract_pdf(self)