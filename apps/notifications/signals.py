"""
Django signals — buyurtma va to'lov eventlarida real-time bildirishnoma yuboradi.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def _push(user_ids, notif_data):
    """Berilgan user_id larning guruhlariga WebSocket xabari yuboradi."""
    try:
        layer = get_channel_layer()
        if not layer:
            return
        for uid in user_ids:
            async_to_sync(layer.group_send)(
                f"user_{uid}",
                {'type': 'send_notification', 'notification': notif_data},
            )
    except Exception:
        pass  # Redis yo'q bo'lsa — xato chiqarmasin


def _save_notif(recipient_ids, notif_type, title, body='', link='', object_id=None):
    """DB ga saqlaydi va WebSocket orqali yuboradi."""
    from .models import Notification
    from django.contrib.auth import get_user_model
    User = get_user_model()

    notifs = []
    for uid in recipient_ids:
        try:
            user = User.objects.get(pk=uid)
            n = Notification.objects.create(
                recipient=user, notif_type=notif_type,
                title=title, body=body, link=link, object_id=object_id,
            )
            notifs.append(n)
            _push([uid], n.to_dict())
        except User.DoesNotExist:
            pass
    return notifs


def _get_admin_manager_ids():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return list(User.objects.filter(
        role__in=('admin', 'manager'), is_active=True
    ).values_list('id', flat=True))


# ── Buyurtma signallari ────────────────────────────────────────────────────────
try:
    from apps.orders.models import Order

    @receiver(post_save, sender=Order)
    def order_created_or_updated(sender, instance, created, **kwargs):
        if created:
            recipients = _get_admin_manager_ids()
            _save_notif(
                recipients,
                notif_type='new_order',
                title=f"Yangi buyurtma #{instance.order_number}",
                body=f"{instance.client.name if instance.client_id else 'Mijoz'} · {int(instance.total_amount or 0):,} so'm",
                link='/orders',
                object_id=instance.pk,
            )

except ImportError:
    pass


# ── To'lov signallari ─────────────────────────────────────────────────────────
try:
    from apps.orders.models import Payment

    @receiver(post_save, sender=Payment)
    def payment_received(sender, instance, created, **kwargs):
        if not created:
            return
        order = instance.order

        # ── Client.total_spent yangilash ──────────────────────────────────────
        try:
            from django.db.models import Sum as _Sum
            client = order.client
            spent = client.orders.aggregate(s=_Sum('paid_amount'))['s'] or 0
            client.total_spent = spent
            client.save(update_fields=['total_spent'])
        except Exception:
            pass

        recipients = _get_admin_manager_ids()
        _save_notif(
            recipients,
            notif_type='payment',
            title=f"To'lov qabul qilindi",
            body=f"#{order.order_number} · +{int(instance.amount or 0):,} so'm",
            link='/orders',
            object_id=order.pk,
        )

except ImportError:
    pass


# ── Ombor signallari ──────────────────────────────────────────────────────────
try:
    from apps.warehouse.models import Stock

    @receiver(post_save, sender=Stock)
    def stock_low_check(sender, instance, **kwargs):
        if instance.quantity <= instance.min_quantity and instance.quantity > 0:
            recipients = _get_admin_manager_ids()
            _save_notif(
                recipients,
                notif_type='low_stock',
                title=f"Omborda kam qoldiq",
                body=f"{instance.product.name} — {instance.quantity} dona qoldi (min: {instance.min_quantity})",
                link='/warehouse',
                object_id=instance.pk,
            )
        elif instance.quantity <= 0:
            recipients = _get_admin_manager_ids()
            _save_notif(
                recipients,
                notif_type='low_stock',
                title=f"Mahsulot tugadi!",
                body=f"{instance.product.name} — stokda 0 dona",
                link='/warehouse',
                object_id=instance.pk,
            )

except ImportError:
    pass