from django.db import models
from django.core.validators import RegexValidator
from apps.common.models import BaseModel

# +998(90) 123-45-67 formatini tekshiruvchi validator
uz_phone_validator = RegexValidator(
    regex=r'^\+998\(\d{2}\) \d{3}-\d{2}-\d{2}$',
    message="Telefon formati: +998(90) 123-45-67"
)


class Client(BaseModel):
    name = models.CharField(max_length=200, verbose_name="Ism familiya")
    phone = models.CharField(
        max_length=20,
        validators=[uz_phone_validator],
        verbose_name="Telefon",
        help_text="Format: +998(90) 123-45-67"
    )
    phone2 = models.CharField(
        max_length=20, blank=True,
        validators=[uz_phone_validator],
        verbose_name="Qo'shimcha telefon",
        help_text="Format: +998(90) 123-45-67"
    )
    email = models.EmailField(blank=True, verbose_name="Email")

    region = models.CharField(max_length=100, blank=True, verbose_name="Viloyat")
    district = models.CharField(max_length=100, blank=True, verbose_name="Tuman")
    mfy = models.CharField(max_length=150, blank=True, verbose_name="MFY")
    address = models.TextField(blank=True, verbose_name="Ko'cha / uy")
    city = models.CharField(max_length=100, blank=True, verbose_name="Shahar")

    avatar = models.ImageField(upload_to='clients/', blank=True, null=True, verbose_name="Rasm")
    notes = models.TextField(blank=True, verbose_name="Izoh")

    # Dashboard uchun zarur bo'lgan ustun (Field)
    total_spent = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name="Jami sarflangan summa"
    )

    is_archived = models.BooleanField(default=False, verbose_name="Arxivlangan")
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name="Arxivlangan vaqt")
    archived_name = models.CharField(max_length=200, blank=True, verbose_name="Arxivdagi ismi")
    archived_phone = models.CharField(max_length=20, blank=True, verbose_name="Arxivdagi telefon")

    class Meta:
        verbose_name = "Mijoz"
        verbose_name_plural = "Mijozlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone})"

    def archive(self):
        from django.utils import timezone
        self.is_archived = True
        self.archived_at = timezone.now()
        self.archived_name = self.name
        self.archived_phone = self.phone
        self.save()

    @property
    def total_orders(self):
        return self.orders.count()

    # DIQQAT: @property total_spent o'chirildi!
    # Uning o'rniga yuqoridagi models.DecimalField ishlatiladi.