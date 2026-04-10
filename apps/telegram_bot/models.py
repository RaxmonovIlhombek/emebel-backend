"""
apps/telegram_bot/models.py

BotSession  — foydalanuvchi holati (RAM emas, DB da)
PaymeTransaction — Payme to'lovlari
ClickTransaction — Click to'lovlari
ScheduledMessage — Celery eslatmalari
"""
import json
from django.db import models
from django.utils import timezone
from apps.common.models import BaseModel


class BotSession(models.Model):
    """
    Telegram bot foydalanuvchi holati — DB da saqlanadi.
    Server restart bo'lsa ham yo'qolmaydi.
    """
    chat_id   = models.CharField(max_length=32, unique=True, db_index=True)
    lang      = models.CharField(max_length=4, default='uz')
    step      = models.CharField(max_length=64, blank=True, default='')
    data      = models.JSONField(default=dict, blank=True)   # cart, register_data, etc.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Bot sessiya"
        verbose_name_plural = "Bot sessiyalar"
        ordering = ['-updated_at']

    def __str__(self):
        return f"chat:{self.chat_id} step:{self.step or '—'}"

    # ── Qulay metodlar ────────────────────────────────────────────────

    @classmethod
    def get(cls, chat_id: str) -> 'BotSession':
        obj, _ = cls.objects.get_or_create(chat_id=str(chat_id))
        return obj

    @classmethod
    def get_lang(cls, chat_id: str) -> str:
        try:
            return cls.objects.get(chat_id=str(chat_id)).lang
        except cls.DoesNotExist:
            return 'uz'

    def set_step(self, step: str, **extra):
        self.step = step
        if extra:
            self.data.update(extra)
        self.save(update_fields=['step', 'data', 'updated_at'])

    def set_data(self, **kwargs):
        self.data.update(kwargs)
        self.save(update_fields=['data', 'updated_at'])

    def clear(self):
        """Holatni tozalash (tilni saqlagan holda)."""
        self.step = ''
        self.data = {}
        self.save(update_fields=['step', 'data', 'updated_at'])

    def get_cart(self) -> list:
        return self.data.get('cart', [])

    def set_cart(self, cart: list):
        self.data['cart'] = cart
        self.save(update_fields=['data', 'updated_at'])

    def add_to_cart(self, product_id: int, name: str, price: float, qty: int):
        cart = self.get_cart()
        for item in cart:
            if item['product_id'] == product_id:
                item['qty'] = qty
                self.set_cart(cart)
                return
        cart.append({'product_id': product_id, 'name': name, 'price': price, 'qty': qty})
        self.set_cart(cart)


class PaymeTransaction(BaseModel):
    """Payme to'lovlari."""
    STATUS_CHOICES = [
        ('pending',   'Kutilmoqda'),
        ('paid',      'To\'langan'),
        ('cancelled', 'Bekor'),
        ('error',     'Xato'),
    ]

    order         = models.ForeignKey('orders.Order', on_delete=models.PROTECT,
                                      related_name='payme_transactions')
    amount        = models.DecimalField(max_digits=16, decimal_places=2,
                                        help_text="Tiyin (100 so'm = 10000 tiyin)")
    payme_id      = models.CharField(max_length=64, blank=True, db_index=True)
    status        = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    create_time   = models.BigIntegerField(null=True, blank=True)
    perform_time  = models.BigIntegerField(null=True, blank=True)
    cancel_time   = models.BigIntegerField(null=True, blank=True)
    reason        = models.IntegerField(null=True, blank=True)
    extra         = models.JSONField(default=dict, blank=True)
    chat_id       = models.CharField(max_length=32, blank=True)

    class Meta:
        verbose_name = "Payme tranzaksiya"
        verbose_name_plural = "Payme tranzaksiyalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"Payme #{self.payme_id or self.pk} — {self.order} ({self.status})"


class ClickTransaction(BaseModel):
    """Click to'lovlari."""
    STATUS_CHOICES = [
        ('pending',   'Kutilmoqda'),
        ('paid',      'To\'langan'),
        ('cancelled', 'Bekor'),
        ('error',     'Xato'),
    ]

    order          = models.ForeignKey('orders.Order', on_delete=models.PROTECT,
                                       related_name='click_transactions')
    amount         = models.DecimalField(max_digits=16, decimal_places=2)
    click_trans_id = models.CharField(max_length=64, blank=True, db_index=True)
    merchant_trans_id = models.CharField(max_length=64, blank=True)
    status         = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    extra          = models.JSONField(default=dict, blank=True)
    chat_id        = models.CharField(max_length=32, blank=True)

    class Meta:
        verbose_name = "Click tranzaksiya"
        verbose_name_plural = "Click tranzaksiyalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"Click #{self.click_trans_id or self.pk} — {self.order} ({self.status})"


class ScheduledMessage(BaseModel):
    """Celery orqali yuborilishi kerak bo'lgan eslatmalar."""
    TYPE_CHOICES = [
        ('delivery_reminder',  'Yetkazish eslatmasi'),
        ('payment_reminder',   'To\'lov eslatmasi'),
        ('order_status',       'Holat o\'zgarishi'),
        ('daily_report',       'Kunlik hisobot'),
        ('low_stock',          'Ombor ogohlantirishi'),
        ('custom',             'Maxsus xabar'),
    ]

    chat_id    = models.CharField(max_length=32)
    msg_type   = models.CharField(max_length=32, choices=TYPE_CHOICES, default='custom')
    text       = models.TextField()
    buttons    = models.JSONField(default=list, blank=True)
    send_at    = models.DateTimeField()
    sent       = models.BooleanField(default=False)
    sent_at    = models.DateTimeField(null=True, blank=True)
    order      = models.ForeignKey('orders.Order', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='scheduled_messages')

    class Meta:
        verbose_name = "Rejali xabar"
        verbose_name_plural = "Rejali xabarlar"
        ordering = ['send_at']
        indexes = [
            models.Index(fields=['sent', 'send_at']),
        ]

    def __str__(self):
        return f"{self.get_msg_type_display()} → {self.chat_id} ({self.send_at.strftime('%d.%m %H:%M')})"