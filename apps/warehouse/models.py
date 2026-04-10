from django.db import models
from apps.products.models import Product
from django.conf import settings


class Stock(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock', verbose_name="Mahsulot")
    quantity = models.IntegerField(default=0, verbose_name="Miqdor")
    min_quantity = models.IntegerField(default=5, verbose_name="Minimal miqdor")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Qoldiq"
        verbose_name_plural = "Ombor qoldiqlari"

    def __str__(self):
        return f"{self.product.name}: {self.quantity} dona"

    @property
    def is_low(self):
        return self.quantity <= self.min_quantity


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('in', 'Kirim'),
        ('out', 'Chiqim'),
        ('adjust', 'Tuzatish'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements', verbose_name="Mahsulot")
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES, verbose_name="Tur")
    quantity = models.IntegerField(verbose_name="Miqdor")
    reason = models.CharField(max_length=200, blank=True, verbose_name="Sabab")
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Kim tomonidan")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sana")

    class Meta:
        verbose_name = "Harakat"
        verbose_name_plural = "Ombor harakatlari"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} ({self.quantity})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        stock, _ = Stock.objects.get_or_create(product=self.product)
        if self.movement_type == 'in':
            stock.quantity += self.quantity
        elif self.movement_type == 'out':
            # Manfiy bo'lishdan himoya
            stock.quantity = max(0, stock.quantity - self.quantity)
        elif self.movement_type == 'adjust':
            # Tuzatishda ham manfiy bo'lmasin
            stock.quantity = max(0, self.quantity)
        stock.save()