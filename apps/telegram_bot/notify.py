"""
notify.py — Telegram xabarnoma yuborish (TO'LIQ KENGAYTIRILGAN)

YANGI:
✅ _send_photo — rasm yuborish
✅ _send_document — fayl/PDF yuborish
✅ notify_order_status_changed — holat o'zgarganda xabar
✅ send_daily_report — kunlik hisobot (kengaytirilgan)
"""
import io
import logging
import requests

import matplotlib
matplotlib.use('Agg') # Serverda grafik oynasi ochilib qolmasligi uchun kerak
import matplotlib.pyplot as plt
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_token():
    return getattr(settings, "TELEGRAM_BOT_TOKEN", "")


def _send(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Oddiy xabar yuborish."""
    if not chat_id or not text:
        return False
    token = _get_token()
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN sozlanmagan!")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
            timeout=5,
        )
        return resp.ok
    except Exception as e:
        logger.error("Telegram xato: %s", e)
        return False


def _send_inline(chat_id: str, text: str, buttons: list, parse_mode: str = "HTML") -> bool:
    """Inline keyboard bilan xabar yuborish."""
    if not chat_id or not text:
        return False
    token = _get_token()
    if not token:
        return False
    try:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if buttons:
            payload["reply_markup"] = {"inline_keyboard": buttons}
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload, timeout=5,
        )
        return resp.ok
    except Exception as e:
        logger.error("Telegram inline xato: %s", e)
        return False


def _send_keyboard(chat_id: str, text: str, keyboard: list, parse_mode: str = "HTML") -> bool:
    """Reply keyboard bilan xabar yuborish."""
    if not chat_id:
        return False
    token = _get_token()
    if not token:
        return False
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": {
                "keyboard": keyboard,
                "resize_keyboard": True,
                "one_time_keyboard": False,
            }
        }
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json=payload, timeout=5,
        )
        return resp.ok
    except Exception as e:
        logger.error("Telegram keyboard xato: %s", e)
        return False


def _edit_inline(chat_id: str, message_id: int, text: str, buttons: list) -> bool:
    """Mavjud xabarni tahrirlash."""
    token = _get_token()
    if not token:
        return False
    try:
        payload = {"chat_id": chat_id, "message_id": message_id,
                   "reply_markup": {"inline_keyboard": buttons}}
        if text:
            payload["text"] = text
            payload["parse_mode"] = "HTML"
            requests.post(f"https://api.telegram.org/bot{token}/editMessageText",
                         json=payload, timeout=5)
        else:
            requests.post(f"https://api.telegram.org/bot{token}/editMessageReplyMarkup",
                         json=payload, timeout=5)
        return True
    except Exception as e:
        logger.error("Telegram edit xato: %s", e)
        return False


# ─── YANGI: 📸 RASM YUBORISH ──────────────────────────────────────────
def _send_photo(chat_id: str, photo, caption: str = "", parse_mode: str = "HTML") -> bool:
    """
    Rasm yuborish.
    photo: file_id (string) yoki bytes
    """
    if not chat_id:
        return False
    token = _get_token()
    if not token:
        return False
    try:
        if isinstance(photo, str):
            # file_id bilan yuborish
            payload = {"chat_id": chat_id, "photo": photo, "parse_mode": parse_mode}
            if caption:
                payload["caption"] = caption
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                json=payload, timeout=10,
            )
        else:
            # bytes bilan yuborish
            files = {"photo": ("photo.jpg", photo, "image/jpeg")}
            data = {"chat_id": chat_id, "parse_mode": parse_mode}
            if caption:
                data["caption"] = caption
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendPhoto",
                files=files, data=data, timeout=15,
            )
        return resp.ok
    except Exception as e:
        logger.error("Telegram photo xato: %s", e)
        return False


# ─── YANGI: 📄 FAYL/PDF YUBORISH ──────────────────────────────────────
def _send_document(chat_id: str, document_bytes: bytes, filename: str,
                   caption: str = "", parse_mode: str = "HTML") -> bool:
    """PDF yoki boshqa fayl yuborish."""
    if not chat_id or not document_bytes:
        return False
    token = _get_token()
    if not token:
        return False
    try:
        files = {"document": (filename, document_bytes, "application/pdf")}
        data = {"chat_id": chat_id, "parse_mode": parse_mode}
        if caption:
            data["caption"] = caption
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendDocument",
            files=files, data=data, timeout=30,
        )
        return resp.ok
    except Exception as e:
        logger.error("Telegram document xato: %s", e)
        return False


def _send_to_roles(*roles, text: str) -> int:
    """Berilgan rollardagi barcha xodimlarga xabar yuborish."""
    from apps.users.models import User
    users = User.objects.filter(
        role__in=roles, is_active=True
    ).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")
    sent = 0
    for u in users:
        if _send(u.telegram_chat_id, text):
            sent += 1
    return sent


def notify_new_registration(user):
    """Yangi foydalanuvchi ro'yxatdan o'tganda adminga xabar."""
    text = (
        f"👤 <b>Yangi ro'yxatdan o'tish!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Foydalanuvchi: <b>{user.username}</b>\n"
        f"Ism: {user.get_full_name() or '—'}\n"
        f"Telefon: {user.phone or '—'}\n"
        f"Rol: {user.get_role_display()}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Tasdiqlash uchun CRM xodimlar bo'limiga kiring."
    )
    _send_to_roles("admin", "manager", text=text)


def notify_password_reset_request(identity):
    """Parolni tiklash so'rovi kelganda adminga xabar."""
    text = (
        f"🔐 <b>Parolni tiklash so'rovi!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Identifikator: <b>{identity}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Iltimos, ushbu foydalanuvchi bilan bog'laning yoki parolini yangilang."
    )
    _send_to_roles("admin", "manager", text=text)


def notify_payment_received(order, amount, method):
    """Muvaffaqiyatli onlayn to'lov haqida adminga xabar."""
    text = (
        f"💰 <b>Yangi onlayn to'lov!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Buyurtma: <b>#{order.order_number}</b>\n"
        f"Mijoz: {order.client.name}\n"
        f"Summa: <b>{amount:,.0f} so'm</b>\n"
        f"Tizim: <b>{method}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"To'lov avtomatik tarzda tasdiqlandi."
    )
    _send_to_roles("admin", "manager", text=text)


def _send_to_roles_inline(*roles, text: str, buttons: list) -> int:
    """Rollardagi xodimlarga inline tugmalar bilan xabar."""
    from apps.users.models import User
    users = User.objects.filter(
        role__in=roles, is_active=True
    ).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")
    sent = 0
    for u in users:
        if _send_inline(u.telegram_chat_id, text, buttons):
            sent += 1
    return sent


# ─── 1. YANGI BUYURTMA → omborchiga ──────────────────────────────────
def notify_new_order(order):
    try:
        items = order.items.select_related("product").all()
        items_text = "\n".join(f"  • {i.product.name} × {i.quantity} dona" for i in items)
        text = (
            f"🛒 <b>Yangi buyurtma!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 Buyurtma: <b>#{order.order_number}</b>\n"
            f"👤 Mijoz: {order.client.name}\n"
            f"📞 Tel: {order.client.phone}\n"
            f"📍 Manzil: {order.delivery_address or '—'}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<b>Mahsulotlar:</b>\n{items_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💰 Jami: <b>{order.total_amount:,.0f} so'm</b>"
        )
        buttons = [[
            {"text": "✅ Tasdiqlash", "callback_data": f"confirm_order_{order.pk}"},
            {"text": "❌ Bekor qilish", "callback_data": f"reject_order_{order.pk}"},
        ]]
        _send_to_roles_inline("worker", "admin", text=text, buttons=buttons)
    except Exception as e:
        logger.error("notify_new_order xato: %s", e)


# ─── 2. BUYURTMA TASDIQLANDI → mijozga ───────────────────────────────
def notify_order_confirmed(order):
    client_user = order.client.user_account
    if not client_user or not client_user.telegram_chat_id:
        return

    from apps.telegram_bot.bot import get_lang
    lang = get_lang(client_user.telegram_chat_id)

    if lang == 'ru':
        text = (
            f"✅ <b>Ваш заказ подтверждён!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 Заказ: <b>#{order.order_number}</b>\n"
            f"📦 Статус: В производстве\n"
            f"💰 Итого: <b>{order.total_amount:,.0f} сум</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"Для оплаты войдите в CRM."
        )
    else:
        text = (
            f"✅ <b>Buyurtmangiz tasdiqlandi!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 Buyurtma: <b>#{order.order_number}</b>\n"
            f"📦 Holat: Ishlab chiqarishda\n"
            f"💰 Jami: <b>{order.total_amount:,.0f} so'm</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"To'lov qilish uchun CRM ga kiring."
        )

    buttons = [[{"text": "🧾 PDF chek" if lang=='uz' else "🧾 PDF чек",
                 "callback_data": f"pdf_order_{order.pk}"}]]
    _send_inline(client_user.telegram_chat_id, text, buttons)


# ─── 3. BUYURTMA BEKOR → mijozga ─────────────────────────────────────
def notify_order_cancelled(order, reason=""):
    client_user = order.client.user_account
    if not client_user or not client_user.telegram_chat_id:
        return

    from apps.telegram_bot.bot import get_lang
    lang = get_lang(client_user.telegram_chat_id)

    if lang == 'ru':
        text = (
            f"❌ <b>Ваш заказ отменён</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 Заказ: <b>#{order.order_number}</b>\n"
        )
        if reason:
            text += f"📝 Причина: {reason}\n"
        text += "━━━━━━━━━━━━━━━\nСвяжитесь с нами для уточнения."
    else:
        text = (
            f"❌ <b>Buyurtmangiz bekor qilindi</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 Buyurtma: <b>#{order.order_number}</b>\n"
        )
        if reason:
            text += f"📝 Sabab: {reason}\n"
        text += "━━━━━━━━━━━━━━━\nQo'shimcha ma'lumot uchun biz bilan bog'laning."

    _send(client_user.telegram_chat_id, text)


# ─── 4. YANGI: BUYURTMA HOLATI O'ZGARGANDA → mijoz + xodimlarga ───────
def notify_order_status_changed(order, old_status: str, changed_by=None):
    try:
        from apps.telegram_bot.bot import get_lang

        status_emoji = {
            'new': '🆕', 'pending': '⚙️', 'production': '🏭',
            'ready': '📦', 'delivered': '🚚', 'completed': '✅', 'cancelled': '❌'
        }
        emoji = status_emoji.get(order.status, '📋')

        # Mijozga xabar
        client_user = order.client.user_account
        if client_user and client_user.telegram_chat_id:
            lang = get_lang(client_user.telegram_chat_id)
            if lang == 'ru':
                msg = (
                    f"{emoji} <b>Статус заказа изменён!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📋 Заказ: <b>#{order.order_number}</b>\n"
                    f"📦 Новый статус: <b>{order.get_status_display()}</b>\n"
                    f"💰 Итого: {order.total_amount:,.0f} сум\n"
                    f"⏳ Остаток: {order.remaining_amount:,.0f} сум"
                )
            else:
                msg = (
                    f"{emoji} <b>Buyurtma holati o'zgardi!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📋 Buyurtma: <b>#{order.order_number}</b>\n"
                    f"📦 Yangi holat: <b>{order.get_status_display()}</b>\n"
                    f"💰 Jami: {order.total_amount:,.0f} so'm\n"
                    f"⏳ Qoldiq: {order.remaining_amount:,.0f} so'm"
                )
            buttons = [[{"text": "🧾 PDF chek" if lang=='uz' else "🧾 PDF чек",
                         "callback_data": f"pdf_order_{order.pk}"}]]
            _send_inline(client_user.telegram_chat_id, msg, buttons)

        # Menejerga xabar (agar worker o'zgartirgan bo'lsa)
        if changed_by and changed_by.role == 'worker' and order.manager:
            if order.manager.telegram_chat_id:
                _send(order.manager.telegram_chat_id,
                    f"{emoji} Buyurtma #{order.order_number} holati o'zgardi: "
                    f"<b>{order.get_status_display()}</b> ({changed_by.get_full_name()})"
                )

        # Yetkazildi holati → buxgalterga
        if order.status == 'delivered':
            _send_to_roles("accountant", "admin", text=(
                f"🚚 <b>Buyurtma yetkazildi!</b>\n"
                f"#{order.order_number} — {order.client.name}\n"
                f"Qoldiq to'lov: {order.remaining_amount:,.0f} so'm"
            ))
    except Exception as e:
        logger.error("notify_order_status_changed xato: %s", e)


# ─── 5. TO'LOV KELDI → buxgalterga ───────────────────────────────────
def notify_payment_submitted(order, payment):
    method_names = {
        "cash": "Naqd", "card": "Karta",
        "transfer": "Bank o'tkazma", "other": "Boshqa",
    }
    text = (
        f"💰 <b>Yangi to'lov keldi!</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📋 Buyurtma: <b>#{order.order_number}</b>\n"
        f"👤 Mijoz: {order.client.name}\n"
        f"💵 Summa: <b>{payment.amount:,.0f} so'm</b>\n"
        f"💳 Usul: {method_names.get(payment.method, payment.method)}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"Qoldiq: {order.remaining_amount:,.0f} so'm\n\n"
        f"CRM da tasdiqlang yoki /javob_{payment.submitted_by.pk if payment.submitted_by else ''} javob bering."
    )
    _send_to_roles("accountant", "admin", text=text)


# ─── 6. TO'LOV TASDIQLANDI → mijozga ─────────────────────────────────
def notify_payment_confirmed(order, payment):
    client_user = order.client.user_account
    if not client_user or not client_user.telegram_chat_id:
        return

    from apps.telegram_bot.bot import get_lang
    lang = get_lang(client_user.telegram_chat_id)
    remaining = order.remaining_amount

    if lang == 'ru':
        text = (
            f"✅ <b>Ваш платёж подтверждён!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 Заказ: <b>#{order.order_number}</b>\n"
            f"💵 Оплачено: <b>{payment.amount:,.0f} сум</b>\n"
        )
        text += "🎉 <b>Полностью оплачено!</b>" if remaining <= 0 else f"⏳ Остаток: <b>{remaining:,.0f} сум</b>"
    else:
        text = (
            f"✅ <b>To'lovingiz tasdiqlandi!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 Buyurtma: <b>#{order.order_number}</b>\n"
            f"💵 To'langan: <b>{payment.amount:,.0f} so'm</b>\n"
        )
        text += "🎉 <b>To'liq to'landi!</b>" if remaining <= 0 else f"⏳ Qoldiq: <b>{remaining:,.0f} so'm</b>"

    _send(client_user.telegram_chat_id, text)


# ─── 7. KAM MAHSULOT → adminga ───────────────────────────────────────
def notify_low_stock():
    from apps.warehouse.models import Stock
    low = Stock.objects.select_related("product").filter(quantity__lte=5, quantity__gt=0)
    empty = Stock.objects.select_related("product").filter(quantity=0)

    if not low.exists() and not empty.exists():
        return

    text = "⚠️ <b>Ombor ogohlantirishi</b>\n━━━━━━━━━━━━━━━\n"
    if empty.exists():
        text += "🔴 <b>Tugagan:</b>\n"
        for s in empty[:10]:
            text += f"  • {s.product.name}\n"
        text += "\n"
    if low.exists():
        text += "🟡 <b>Kam qolgan:</b>\n"
        for s in low[:10]:
            text += f"  • {s.product.name} — {s.quantity} dona\n"

    _send_to_roles("admin", "worker", text=text)


# ─── 8. KUNLIK HISOBOT (KENGAYTIRILGAN) ──────────────────────────────
def send_daily_report():
    try:
        from apps.orders.models import Order, Payment
        from apps.clients.models import Client
        from django.db.models import Sum, Count
        from django.utils import timezone

        today = timezone.now().date()
        today_orders = Order.objects.filter(created_at__date=today)
        today_payments = Payment.objects.filter(created_at__date=today, is_confirmed=True)
        new_clients = Client.objects.filter(created_at__date=today)

        orders_count = today_orders.count()
        revenue_today = today_payments.aggregate(s=Sum("amount"))["s"] or 0
        new_clients_cnt = new_clients.count()

        total_debt_qs = Order.objects.filter(payment_status__in=["unpaid", "partial"])
        total_debt = 0
        for o in total_debt_qs:
            total_debt += float(o.total_amount) - float(o.paid_amount)

        statuses = dict(
            Order.objects.values("status").annotate(c=Count("id")).values_list("status", "c")
        )

        # Eng ko'p sotilgan mahsulotlar (bugun)
        from apps.orders.models import OrderItem
        from django.db.models import Sum as DSum
        top_products = (
            OrderItem.objects.filter(order__created_at__date=today)
            .values('product__name')
            .annotate(total_qty=DSum('quantity'))
            .order_by('-total_qty')[:3]
        )
        top_text = ""
        for p in top_products:
            top_text += f"  • {p['product__name']}: {p['total_qty']} dona\n"

        text = (
            f"📊 <b>Kunlik hisobot — {today.strftime('%d.%m.%Y')}</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"🛒 Bugungi buyurtmalar: <b>{orders_count} ta</b>\n"
            f"💰 Bugungi tushumlar: <b>{revenue_today:,.0f} so'm</b>\n"
            f"👤 Yangi mijozlar: <b>{new_clients_cnt} ta</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📋 <b>Buyurtmalar holati:</b>\n"
            f"  🆕 Yangi: {statuses.get('new', 0)} ta\n"
            f"  ⚙️ Jarayonda: {statuses.get('pending', 0) + statuses.get('production', 0)} ta\n"
            f"  ✅ Tayyor: {statuses.get('ready', 0)} ta\n"
            f"  🚚 Yetkazildi: {statuses.get('delivered', 0)} ta\n"
            f"  ❌ Bekor: {statuses.get('cancelled', 0)} ta\n"
            f"━━━━━━━━━━━━━━━\n"
            f"💸 Umumiy qarz: <b>{total_debt:,.0f} so'm</b>"
        )
        if top_text:
            text += f"\n━━━━━━━━━━━━━━━\n🏆 <b>Bugungi eng ko'p:</b>\n{top_text}"

        _send_to_roles("admin", text=text)
        notify_low_stock()
    except Exception as e:
        logger.error("send_daily_report xato: %s", e)


def send_visual_report(chat_id):
    from apps.orders.models import Order
    from django.utils import timezone
    import datetime
    from django.db.models import Sum

    # Oxirgi 7 kunlik ma'lumot
    days = []
    sales = []
    for i in range(6, -1, -1):
        date = timezone.now().date() - datetime.timedelta(days=i)
        total = Order.objects.filter(created_at__date=date).aggregate(s=Sum('total_amount'))['s'] or 0
        days.append(date.strftime('%d-%b'))
        sales.append(float(total) / 1_000_000)  # Million so'mda

    plt.figure(figsize=(8, 4))
    plt.plot(days, sales, marker='o', color='#f97316', linewidth=3) # Orange brand color
    plt.fill_between(days, sales, color='#f97316', alpha=0.1)
    plt.title("Haftalik savdo dinamikasi (mln so'm)", fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    _send_photo(chat_id, buf.read(), caption="📊 <b>So'nggi 7 kunlik savdo dinamikasi</b>")
    plt.close()