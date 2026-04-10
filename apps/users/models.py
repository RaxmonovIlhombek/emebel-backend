from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

uz_phone_validator = RegexValidator(
    regex=r'^\+998\(\d{2}\) \d{3}-\d{2}-\d{2}$',
    message="Telefon formati: +998(90) 123-45-67"
)


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin',      'Admin'),
        ('manager',    'Menejer'),
        ('accountant', 'Buxgalter'),
        ('worker',     'Omborchi'),
        ('client',     'Mijoz'),
    )
    role  = models.CharField(max_length=20, choices=ROLE_CHOICES, default='manager', verbose_name="Rol")
    phone = models.CharField(
        max_length=20, unique=True, blank=True, null=True,
        validators=[uz_phone_validator],
        verbose_name="Telefon",
        help_text="Format: +998(90) 123-45-67"
    )
    avatar           = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Rasm")
    telegram_chat_id = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telegram Chat ID")
    telegram_username = models.CharField(max_length=64, blank=True, null=True, verbose_name="Telegram Username (@siz)")
    client_profile   = models.OneToOneField(
        'clients.Client',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='user_account',
        verbose_name="Mijoz profili"
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_client(self):
        return self.role == 'client'

    @property
    def is_staff_member(self):
        return self.role in ('admin', 'manager', 'accountant', 'worker')


class Message(models.Model):
    sender   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages',     verbose_name="Yuboruvchi")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages', verbose_name="Qabul qiluvchi")
    body     = models.TextField(verbose_name="Xabar matni")
    is_read  = models.BooleanField(default=False, verbose_name="O'qildi")
    order_ref = models.IntegerField(null=True, blank=True, verbose_name="Buyurtma ID")
    is_order_notification = models.BooleanField(default=False, verbose_name="Buyurtma bildirishi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Vaqt")

    class Meta:
        verbose_name = "Xabar"
        verbose_name_plural = "Xabarlar"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender} → {self.receiver}: {self.body[:40]}"