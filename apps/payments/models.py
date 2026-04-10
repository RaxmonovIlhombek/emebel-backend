from django.db import models
from apps.common.models import BaseModel
from apps.orders.models import Order

class Transaction(BaseModel):
    """Click/Payme to'lovlari tarixi"""
    PROVIDER_CHOICES = [
        ('click', 'Click'),
        ('payme', 'Payme'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('success', 'Muvaffaqiyatli'),
        ('failed',  'Xato'),
    ]
    
    provider       = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    order          = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='transactions')
    amount         = models.DecimalField(max_digits=14, decimal_places=2)
    provider_id    = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tashqi ID")
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    request_data   = models.JSONField(null=True, blank=True)
    response_data  = models.JSONField(null=True, blank=True)
    error_message  = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Tranzaksiya"
        verbose_name_plural = "Tranzaksiyalar"
