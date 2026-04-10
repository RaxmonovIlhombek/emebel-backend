from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('new_order',     'Yangi buyurtma'),
        ('status_change', "Holat o'zgardi"),
        ('payment',       "To'lov qilindi"),
        ('overdue',       'Kechikkan buyurtma'),
        ('low_stock',     'Kam qoldiq'),
        ('message',       'Yangi xabar'),
        ('system',        'Tizim'),
    ]

    recipient   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='notifications')
    notif_type  = models.CharField(max_length=30, choices=TYPE_CHOICES, default='system')
    title       = models.CharField(max_length=255)
    body        = models.TextField(blank=True)
    link        = models.CharField(max_length=255, blank=True)
    is_read     = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    # Trigger qilgan obyektni tracking uchun (ixtiyoriy)
    object_id   = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.notif_type}] {self.recipient} — {self.title}"

    def to_dict(self):
        return {
            'id':         self.pk,
            'type':       self.notif_type,
            'title':      self.title,
            'body':       self.body,
            'link':       self.link,
            'is_read':    self.is_read,
            'created_at': self.created_at.isoformat(),
        }