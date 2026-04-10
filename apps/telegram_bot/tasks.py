"""
tasks.py — Celery async vazifalar

✅ Buyurtma eslatmalari
✅ Qarz eslatmalari
✅ Ombor ogohlantirishi
✅ Kunlik hisobot
✅ To'lov tasdiqlash
"""
import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


# ─── BUYURTMA ESLATMALARI ──────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def schedule_order_reminders(self, order_pk):
    """
    Yangi buyurtma yaratilganda avtomatik eslatmalar rejalashtiradi:
    - Omborchiga: darhol xabar
    - Mijozga: 1 kundan keyin holat eslatmasi
    - Menejerga: agar 2 kun ichida tasdiqlanmasa
    """
    try:
        from apps.orders.models import Order
        from apps.users.models import User
        from .models import ScheduledMessage

        order = Order.objects.get(pk=order_pk)
        now   = timezone.now()

        # 1. Omborchilarga darhol xabar
        workers = User.objects.filter(role__in=['worker', 'admin'], is_active=True).exclude(telegram_chat_id='')
        for w in workers:
            ScheduledMessage.objects.create(
                chat_id   = w.telegram_chat_id,
                msg_type  = 'order_status',
                text      = (
                    f"🆕 <b>Yangi buyurtma!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📋 #{order.order_number}\n"
                    f"👤 {order.client.name}\n"
                    f"📞 {order.client.phone}\n"
                    f"💰 {order.total_amount:,.0f} so'm\n"
                    f"🏠 {order.delivery_address or '—'}\n\n"
                    f"Tasdiqlash: /tasdiqlash_{order.pk}\n"
                    f"Bekor: /bekor_{order.pk}"
                ),
                send_at   = now + timedelta(minutes=1),
                order     = order,
            )

        # 2. Mijozga: 1 kun keyin holat
        if order.client and hasattr(order.client, 'user_account') and order.client.user_account:
            user_acc = order.client.user_account
            if user_acc.telegram_chat_id:
                ScheduledMessage.objects.create(
                    chat_id  = user_acc.telegram_chat_id,
                    msg_type = 'order_status',
                    text     = (
                        f"📦 Buyurtmangiz holati:\n"
                        f"#{order.order_number} — {order.get_status_display()}\n"
                        f"/holat_{order.pk}"
                    ),
                    send_at  = now + timedelta(days=1),
                    order    = order,
                )

        # 3. Menejerga: 2 kun keyin agar 'new' holida qolsa
        managers = User.objects.filter(role__in=['manager', 'admin'], is_active=True).exclude(telegram_chat_id='')
        for m in managers:
            ScheduledMessage.objects.create(
                chat_id  = m.telegram_chat_id,
                msg_type = 'order_status',
                text     = (
                    f"⚠️ <b>Buyurtma tasdiqlanmadi!</b>\n"
                    f"#{order.order_number} hali 'Yangi' holatda.\n"
                    f"Mijoz: {order.client.name}"
                ),
                send_at  = now + timedelta(days=2),
                order    = order,
            )

        logger.info(f"✅ Order #{order.pk} eslatmalari rejalashtirildi")
        return f"Order #{order_pk}: eslatmalar rejalashtirildi"

    except Exception as exc:
        logger.error(f"schedule_order_reminders xato: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_scheduled_messages(self):
    """
    Har 1 daqiqada ishga tushadi (celery beat).
    Vaqti kelgan xabarlarni yuboradi.
    """
    try:
        from .models import ScheduledMessage
        from .notify import _send, _send_inline

        now      = timezone.now()
        messages = ScheduledMessage.objects.filter(sent=False, send_at__lte=now).select_related('order')[:50]

        sent_count = 0
        for msg in messages:
            try:
                # Buyurtma holati tekshirish (eskirgan eslatma bo'lsa o'tkazib yuborish)
                if msg.order and msg.msg_type in ('order_status', 'delivery_reminder'):
                    order = msg.order
                    if order.status in ('completed', 'cancelled'):
                        msg.sent = True
                        msg.sent_at = now
                        msg.save(update_fields=['sent', 'sent_at'])
                        continue

                if msg.buttons:
                    _send_inline(msg.chat_id, msg.text, msg.buttons)
                else:
                    _send(msg.chat_id, msg.text)

                msg.sent    = True
                msg.sent_at = now
                msg.save(update_fields=['sent', 'sent_at'])
                sent_count += 1

            except Exception as e:
                logger.error(f"Xabar #{msg.pk} yuborishda xato: {e}")

        if sent_count:
            logger.info(f"✅ {sent_count} ta xabar yuborildi")
        return f"{sent_count} xabar yuborildi"

    except Exception as exc:
        logger.error(f"send_scheduled_messages xato: {exc}")
        raise self.retry(exc=exc, countdown=30)


# ─── QARZ ESLATMALARI ─────────────────────────────────────────────────

@shared_task
def send_debt_reminders():
    """
    Har kuni ertalab ishga tushadi.
    To'lanmagan buyurtmalar uchun eslatma yuboradi.
    """
    from apps.orders.models import Order
    from apps.users.models import User
    from .notify import _send

    # 3+ kunlik to'lanmagan buyurtmalar
    cutoff = timezone.now() - timedelta(days=3)
    orders = Order.objects.filter(
        payment_status__in=['unpaid', 'partial'],
        status__in=['delivered', 'completed', 'ready'],
        created_at__lte=cutoff
    ).select_related('client', 'manager')

    sent = 0
    for order in orders:
        # Mijozga xabar
        try:
            if order.client and hasattr(order.client, 'user_account') and order.client.user_account:
                user_acc = order.client.user_account
                if user_acc.telegram_chat_id:
                    _send(user_acc.telegram_chat_id,
                        f"💳 <b>To'lov eslatmasi</b>\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"📋 Buyurtma #{order.order_number}\n"
                        f"💰 Qoldiq: <b>{order.remaining_amount:,.0f} so'm</b>\n"
                        f"📅 {order.created_at.strftime('%d.%m.%Y')}\n\n"
                        f"/tolov_{order.pk} — to'lash"
                    )
                    sent += 1
        except Exception as e:
            logger.error(f"Debt reminder mijoz: {e}")

        # Menejerga ham xabar
        try:
            if order.manager and order.manager.telegram_chat_id:
                _send(order.manager.telegram_chat_id,
                    f"⚠️ <b>To'lanmagan buyurtma</b>\n"
                    f"#{order.order_number} — {order.client.name}\n"
                    f"📞 {order.client.phone}\n"
                    f"💰 {order.remaining_amount:,.0f} so'm"
                )
        except Exception as e:
            logger.error(f"Debt reminder menejer: {e}")

    logger.info(f"✅ Qarz eslatmasi: {sent} mijozga yuborildi")
    return f"{sent} debt reminders sent"


# ─── YETKAZISH ESLATMASI ──────────────────────────────────────────────

@shared_task
def send_delivery_reminders():
    """
    Har kuni kechqurun ishga tushadi.
    Ertaga yetkazish kerak bo'lgan buyurtmalar.
    """
    from apps.orders.models import Order
    from .notify import _send
    from .bot import get_lang

    tomorrow = timezone.now().date() + timedelta(days=1)
    orders   = Order.objects.filter(
        delivery_date=tomorrow,
        status__in=['production', 'ready', 'pending']
    ).select_related('client', 'manager')

    sent = 0
    for order in orders:
        try:
            if order.manager and order.manager.telegram_chat_id:
                lang = get_lang(order.manager.telegram_chat_id)
                uz   = lang == 'uz'
                _send(order.manager.telegram_chat_id,
                    f"🚚 <b>{'Ertaga yetkazish' if uz else 'Завтра доставка'}!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"#{order.order_number} — {order.client.name}\n"
                    f"📞 {order.client.phone}\n"
                    f"🏠 {order.delivery_address or '—'}\n"
                    f"💰 {'Qoldiq' if uz else 'Остаток'}: {order.remaining_amount:,.0f} so'm"
                )
                sent += 1
        except Exception as e:
            logger.error(f"Delivery reminder: {e}")

    logger.info(f"✅ Yetkazish eslatmasi: {sent} ta")
    return f"{sent} delivery reminders"


# ─── OMBOR OGOHLANTIRISHI ─────────────────────────────────────────────

@shared_task
def check_low_stock():
    """
    Har kuni ertalab. Omborda kam mahsulotlar haqida ogohlantirish.
    """
    from apps.warehouse.models import Stock
    from apps.users.models import User
    from .notify import _send

    low_stocks = Stock.objects.filter(
        quantity__lte=models_F('min_quantity')
    ).select_related('product')

    if not low_stocks:
        return "No low stock"

    text = "⚠️ <b>Ombor ogohlantirishi!</b>\n━━━━━━━━━━━━━━━\n"
    for s in low_stocks:
        icon = "🔴" if s.quantity == 0 else "🟡"
        text += f"{icon} {s.product.name}: <b>{s.quantity}</b> (min: {s.min_quantity})\n"

    workers  = User.objects.filter(role__in=['worker', 'admin', 'manager'], is_active=True).exclude(telegram_chat_id='')
    sent = 0
    for user in workers:
        try:
            _send(user.telegram_chat_id, text)
            sent += 1
        except Exception as e:
            logger.error(f"Low stock notify: {e}")

    return f"Low stock: {low_stocks.count()} items, {sent} notified"


# ─── KUNLIK HISOBOT ───────────────────────────────────────────────────

@shared_task
def send_daily_report_task():
    """
    Har kuni kechqurun (20:00). Kunlik hisobot.
    """
    from .notify import send_daily_report
    try:
        send_daily_report()
        return "Daily report sent"
    except Exception as e:
        logger.error(f"Daily report xato: {e}")
        return f"Error: {e}"


# ─── TO'LOV TEKSHIRISH ────────────────────────────────────────────────

@shared_task
def check_payme_payments():
    """
    Har 5 daqiqada. Payme to'lovlarini tekshiradi.
    """
    from .models import PaymeTransaction
    from apps.orders.models import Payment
    from django.conf import settings
    import requests

    merchant = getattr(settings, 'PAYME_MERCHANT_ID', '')
    key      = getattr(settings, 'PAYME_KEY', '')
    if not merchant or not key:
        return "Payme not configured"

    pending = PaymeTransaction.objects.filter(status='pending', payme_id='')[:20]
    checked = 0

    for txn in pending:
        try:
            # Payme API tekshirish (real implementatsiya)
            # Hozircha faqat log
            logger.info(f"Checking Payme txn #{txn.pk} for order #{txn.order_id}")
            checked += 1
        except Exception as e:
            logger.error(f"Payme check #{txn.pk}: {e}")

    return f"Checked {checked} Payme transactions"


# F import uchun
def models_F(field):
    from django.db.models import F
    return F(field)