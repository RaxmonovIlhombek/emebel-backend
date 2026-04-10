"""
bot.py — Telegram bot (PRO versiya)

DB-backed state (BotSession), yaxshilangan menyu,
Payme/Click tolov, WebApp katalog, reply keyboard
"""
import json
import logging
import io
import requests

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .notify import _send, _send_keyboard, _send_inline, _edit_inline, _send_document, _send_photo, send_visual_report
from .ai import get_ai_response

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    SCANNER_AVAILABLE = True
except ImportError:
    SCANNER_AVAILABLE = False
    logger.warning("opencv-python topilmadi.")


def decode_barcode_from_bytes(img_bytes):
    """Rasm bytes dan barcode/QR kod o'qiydi (faqat OpenCV - ishonchli).
    Returns: str yoki None
    """
    if not SCANNER_AVAILABLE: return None
    try:
        arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None: return None
        
        # Skanerlarni yaratish
        qr_detector = cv2.QRCodeDetector()
        try:
            barcode_detector = cv2.barcode.BarcodeDetector()
        except: barcode_detector = None

        # Rasmni turli hil o'zgartirishlarda proba qilish (PRO logic)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        candidates = [
            gray,
            cv2.GaussianBlur(gray, (5, 5), 0),
            cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        ]
        
        for proc in candidates:
            # 1. QR qidiruv
            data, _, _ = qr_detector.detectAndDecode(proc)
            if data: return data.strip()
            
            # 2. Barcode qidiruv
            if barcode_detector:
                ok, info, _, _ = barcode_detector.detectAndDecode(proc)
                if ok and info and info[0]: return info[0].strip()
                
            # 3. Agar joriy qatlamda topilmasa, o'lchamni kattalashtirib ko'ramiz
            big = cv2.resize(proc, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            data_big, _, _ = qr_detector.detectAndDecode(big)
            if data_big: return data_big.strip()
            
            if barcode_detector:
                ok_big, info_big, _, _ = barcode_detector.detectAndDecode(big)
                if ok_big and info_big and info_big[0]: return info_big[0].strip()

        return None
    except Exception as e:
        logger.error(f"Barcode o'qishda xato: {e}")
        return None


def download_photo_bytes(file_id):
    """Telegram file_id dan rasm bytes yuklab oladi."""
    try:
        from django.conf import settings
        token = settings.TELEGRAM_BOT_TOKEN
        file_info = requests.get(
            f"https://api.telegram.org/bot{token}/getFile",
            params={"file_id": file_id},
            timeout=10
        ).json()
        file_path = file_info['result']['file_path']
        img_url   = f"https://api.telegram.org/file/bot{token}/{file_path}"
        resp      = requests.get(img_url, timeout=15)
        return resp.content
    except Exception as e:
        logger.error(f"Rasm yuklab olishda xato: {e}")
        return None

LANG = {
    'uz': {
        'welcome_known': "✅ <b>Ulandi!</b>\n\nSalom, {name}!\nRol: {role}\n\n/yordam — buyruqlar",
        'welcome_unknown': "👋 <b>e-Mebel CRM</b>\n\nTelegram ID: <code>{chat_id}</code>\n\nCRM da profilingizga shu IDni kiriting.\n\n/royxat — ro'yxatdan o'ting.",
        'no_access': "❌ Ruxsat yo'q.",
        'not_linked': "❌ Ulanmagan. /start yuboring.",
        'order_not_found': "❌ Buyurtma topilmadi.",
        'already_processed': "ℹ️ Buyurtma #{num} allaqachon {status}.",
        'no_stock': "❌ <b>Omborda yetarli mahsulot yo'q:</b>\n{items}",
        'confirmed': "✅ Buyurtma <b>#{num}</b> tasdiqlandi!",
        'cancelled_order': "🚫 Buyurtma <b>#{num}</b> bekor qilindi.",
        'no_orders': "📭 Hali buyurtma yo'q.",
        'orders_title': "📦 <b>Buyurtmalar:</b>\n━━━━━━━━━━━━━━━\n",
        'stock_title': "🏭 <b>Ombor:</b>\n━━━━━━━━━━━━━━━\n",
        'stock_empty': "📭 Ombor bo'sh.",
        'select_lang': "🌐 Tilni tanlang:",
        'lang_set': "✅ O'zbek tili!",
        'menu_title': "📋 <b>Menyu</b>\nTugmalardan foydalaning 👇",
        'order_step1': "🛍 <b>Buyurtma berish</b>\n\nMahsulotlar:",
        'order_cart_add': "✅ {name} ({qty} dona) savatga qo'shildi.",
        'order_cart_empty': "🛒 Savat bo'sh.",
        'order_qty_ask': "📦 <b>{name}</b> — {price:,.0f} so'm\n\nNechta? (1-100)",
        'order_invalid_qty': "❌ 1 dan 100 gacha raqam kiriting.",
        'order_address_ask': "🏠 Yetkazish manzilini yozing:\n\n📍 Yoki joylashuvingizni yuboring.",
        'order_confirm_text': "📋 <b>Tasdiqlash</b>\n━━━━━━━━━━━━━━━\n{items}\n━━━━━━━━━━━━━━━\n💰 Jami: <b>{total:,.0f} so'm</b>\n🏠 {address}\n\nTasdiqlaysizmi?",
        'order_placed': "✅ <b>Buyurtma qabul qilindi!</b>\n\nBuyurtma #{num}",
        'order_cancelled_user': "❌ Bekor qilindi.",
        'roles': {'admin': 'Admin', 'accountant': 'Buxgalter', 'worker': 'Omborchi', 'manager': 'Menejer', 'client': 'Mijoz'},
        'photo_received': "📸 Rasm qabul qilindi. Nima uchun?",
        'receipt_saved': "✅ To'lov cheki saqlandi!",
        'chat_send': "💬 Xabar yozing:",
        'chat_sent': "✅ Yuborildi!",
        'chat_reply': "💬 Yuborildi.",
        'location_saved': "📍 Saqlandi!",
        'register_name': "👤 <b>Ro'yxatdan o'tish</b>\n\nIsmingizni kiriting:",
        'register_phone': "📞 Telefon: (+998901234567)",
        'register_done': "✅ <b>Ro'yxatdan o'tdingiz!</b>\n\nIsm: {name}\nTel: {phone}",
        'register_exists': "ℹ️ Allaqachon ro'yxatdan o'tgansiz.",
        'pdf_preparing': "⏳ PDF tayyorlanmoqda...",
        'pay_link_sent': "💳 To'lov havolasi yuborildi!",
        'catalog_btn': "🛍 Katalogni ochish",
    },
    'ru': {
        'welcome_known': "✅ <b>Подключено!</b>\n\nПривет, {name}!\nРоль: {role}\n\n/help — команды",
        'welcome_unknown': "👋 <b>e-Mebel CRM</b>\n\nID: <code>{chat_id}</code>\n\nВведите этот ID в профиль CRM.\n\n/register — регистрация.",
        'no_access': "❌ Нет доступа.",
        'not_linked': "❌ Не подключены. Отправьте /start.",
        'order_not_found': "❌ Заказ не найден.",
        'already_processed': "ℹ️ Заказ #{num} уже {status}.",
        'no_stock': "❌ <b>Недостаточно товара:</b>\n{items}",
        'confirmed': "✅ Заказ <b>#{num}</b> подтверждён!",
        'cancelled_order': "🚫 Заказ <b>#{num}</b> отменён.",
        'no_orders': "📭 Заказов пока нет.",
        'orders_title': "📦 <b>Заказы:</b>\n━━━━━━━━━━━━━━━\n",
        'stock_title': "🏭 <b>Склад:</b>\n━━━━━━━━━━━━━━━\n",
        'stock_empty': "📭 Склад пуст.",
        'select_lang': "🌐 Выберите язык:",
        'lang_set': "✅ Русский язык!",
        'menu_title': "📋 <b>Меню</b>\nИспользуйте кнопки 👇",
        'order_step1': "🛍 <b>Оформить заказ</b>\n\nТовары:",
        'order_cart_add': "✅ {name} ({qty} шт.) в корзине.",
        'order_cart_empty': "🛒 Корзина пуста.",
        'order_qty_ask': "📦 <b>{name}</b> — {price:,.0f} сум\n\nСколько? (1-100)",
        'order_invalid_qty': "❌ Введите число 1-100.",
        'order_address_ask': "🏠 Адрес доставки:\n\n📍 Или отправьте геолокацию.",
        'order_confirm_text': "📋 <b>Подтверждение</b>\n━━━━━━━━━━━━━━━\n{items}\n━━━━━━━━━━━━━━━\n💰 Итого: <b>{total:,.0f} сум</b>\n🏠 {address}\n\nПодтверждаете?",
        'order_placed': "✅ <b>Заказ принят!</b>\n\nЗаказ #{num}",
        'order_cancelled_user': "❌ Отменён.",
        'roles': {'admin': 'Администратор', 'accountant': 'Бухгалтер', 'worker': 'Кладовщик', 'manager': 'Менеджер', 'client': 'Клиент'},
        'photo_received': "📸 Фото получено. Для чего?",
        'receipt_saved': "✅ Чек сохранён!",
        'chat_send': "💬 Напишите сообщение:",
        'chat_sent': "✅ Отправлено!",
        'chat_reply': "💬 Отправлено.",
        'location_saved': "📍 Сохранено!",
        'register_name': "👤 <b>Регистрация</b>\n\nВведите имя:",
        'register_phone': "📞 Телефон: (+998901234567)",
        'register_done': "✅ <b>Зарегистрировались!</b>\n\nИмя: {name}\nТел: {phone}",
        'register_exists': "ℹ️ Вы уже зарегистрированы.",
        'pdf_preparing': "⏳ Готовится PDF...",
        'pay_link_sent': "💳 Ссылка отправлена!",
        'catalog_btn': "🛍 Открыть каталог",
    }
}
# ─── ROLE HELPERS ──────────────────────────────────────────────────────

def get_user(chat_id):
    from apps.users.models import User
    return User.objects.filter(telegram_chat_id=chat_id).first()

def is_staff(user):
    return user and user.role in ['admin', 'manager', 'accountant', 'worker']

def is_management(user):
    return user and user.role in ['admin', 'manager', 'accountant']

def is_admin_or_manager(user):
    return user and user.role in ['admin', 'manager']

# ─── DB STATE ─────────────────────────────────────────────────────────

def get_session(chat_id):
    from .models import BotSession
    return BotSession.get(chat_id)

def get_lang(chat_id):
    from .models import BotSession
    return BotSession.get_lang(chat_id)

def t(chat_id, key, **kwargs):
    lang = get_lang(chat_id)
    text = LANG[lang].get(key, LANG['uz'].get(key, key))
    return text.format(**kwargs) if kwargs else text

def get_state(chat_id):
    s = get_session(chat_id)
    return {'step': s.step, 'lang': s.lang, **s.data}

def set_state(chat_id, **kwargs):
    s = get_session(chat_id)
    if 'step' in kwargs: s.step = kwargs.pop('step')
    if 'lang' in kwargs: s.lang = kwargs.pop('lang')
    if kwargs: s.data.update(kwargs)
    s.save(update_fields=['step', 'lang', 'data', 'updated_at'])

def clear_state(chat_id):
    s = get_session(chat_id)
    lang = s.lang
    s.step = ''; s.data = {}; s.lang = lang
    s.save(update_fields=['step', 'data', 'updated_at'])


# ─── WEBHOOK ──────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def telegram_webhook(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"ok": False}, status=400)

    if "callback_query" in data:
        _handle_callback(data["callback_query"])
        return JsonResponse({"ok": True})

    message = data.get("message") or data.get("edited_message")
    if not message:
        return JsonResponse({"ok": True})

    chat_id     = str(message.get("chat", {}).get("id", ""))
    text        = message.get("text", "").strip()
    tg_username = message.get("from", {}).get("username", "")

    if not chat_id:
        return JsonResponse({"ok": True})

    if "photo"    in message: _handle_photo(chat_id, message);          return JsonResponse({"ok": True})
    if "location" in message: _handle_location(chat_id, message["location"]); return JsonResponse({"ok": True})
    if "document" in message: _handle_document(chat_id, message);       return JsonResponse({"ok": True})

    state = get_state(chat_id)
    step  = state.get("step", "")

    # Reply keyboard tugmalari
    menu_map = {
        "📦 Buyurtmalarim": _handle_my_orders, "📦 Мои заказы": _handle_my_orders,
        "📦 Buyurtmalar": _handle_my_orders, "📦 Заказы": _handle_my_orders,
        "🛍 Buyurtma berish": _handle_order_start, "🛍 Оформить заказ": _handle_order_start,
        "📊 Statistika": _handle_statistics, "📊 Статистика": _handle_statistics,
        "📊 Dashboard": _handle_dashboard,
        "🤖 AI Yordamchi": _handle_ai_start,
        "🏭 Ombor": _handle_stock, "🏭 Склад": _handle_stock,
        "💬 Chat": _handle_chat_start, "💬 Чат": _handle_chat_start,
        "📊 Hisobot": _handle_report, "📊 Отчёт": _handle_report,
        "❓ Yordam": _handle_help, "❓ Помощь": _handle_help,
        "🛍 Katalog": _handle_catalog, "🛍 Каталог": _handle_catalog,
        "💳 To'lov": _handle_payment_start, "💳 Оплата": _handle_payment_start,
    }
    if text in menu_map:
        menu_map[text](chat_id)
        return JsonResponse({"ok": True})

    if step == "waiting_qty":             _handle_order_qty(chat_id, text)
    elif step == "waiting_address":       _handle_order_address(chat_id, text)
    elif step == "waiting_chat_message":  _handle_chat_send(chat_id, text)
    elif step == "waiting_reply_message": _handle_chat_reply(chat_id, text)
    elif step == "register_name":         _handle_register_name(chat_id, text)
    elif step == "register_phone":        _handle_register_phone(chat_id, text)
    elif text.startswith("/start"):       _handle_start(chat_id, tg_username)
    elif text in ("/menu", "/menyu"):     _handle_menu(chat_id)
    elif text in ("/til", "/lang"):       _handle_lang_select(chat_id)
    elif text in ("/buyurtmalar", "/orders"): _handle_my_orders(chat_id)
    elif text in ("/hisobot", "/report"): _handle_report(chat_id)
    elif text in ("/ombor", "/stock"):    _handle_stock(chat_id)
    elif text in ("/yordam", "/help"):    _handle_help(chat_id)
    elif text in ("/buyurtma", "/order"): _handle_order_start(chat_id)
    elif text in ("/statistika", "/stat"):_handle_statistics(chat_id)
    elif text in ("/dashboard", "/grafik"): _handle_dashboard(chat_id)
    elif text.startswith("/broadcast "): _handle_broadcast(chat_id, text)
    elif text in ("/chat", "/xabar"):     _handle_chat_start(chat_id)
    elif text in ("/ai", "/savol"):       _handle_ai_start(chat_id)
    elif text in ("/royxat", "/register"):_handle_register_start(chat_id)
    elif text in ("/katalog", "/catalog"):_handle_catalog(chat_id)
    elif text.startswith("/tasdiqlash_"): _handle_confirm_order(chat_id, text)
    elif text.startswith("/bekor_"):      _handle_reject_order(chat_id, text)
    elif text.startswith("/holat_"):      _handle_order_status(chat_id, text)
    elif text.startswith("/chek_"):       _handle_send_pdf_receipt(chat_id, text)
    elif text.startswith("/javob_"):      _handle_reply_start(chat_id, text)
    elif text.startswith("/tolov_"):      _handle_payment_for_order(chat_id, text)
    else:                                 _handle_unknown_text(chat_id, text)

    return JsonResponse({"ok": True})


# ─── CALLBACK ─────────────────────────────────────────────────────────

def _handle_callback(cb):
    chat_id = str(cb["message"]["chat"]["id"])
    msg_id  = cb["message"]["message_id"]
    data    = cb.get("data", "")

    cb_map = {
        "lang_uz":     lambda: (set_state(chat_id, lang='uz'), _edit_inline(chat_id, msg_id, t(chat_id,'lang_set'),[]), _handle_after_lang(chat_id)),
        "lang_ru":     lambda: (set_state(chat_id, lang='ru'), _edit_inline(chat_id, msg_id, t(chat_id,'lang_set'),[]), _handle_after_lang(chat_id)),
        "menu_orders": lambda: _handle_my_orders(chat_id),
        "menu_order_new": lambda: _handle_order_start(chat_id),
        "menu_help":   lambda: _handle_help(chat_id),
        "menu_stock":  lambda: _handle_stock(chat_id),
        "menu_report": lambda: _handle_report(chat_id),
        "menu_stat":   lambda: _handle_statistics(chat_id),
        "menu_chat":   lambda: _handle_chat_start(chat_id),
        "menu_register": lambda: _handle_register_start(chat_id),
        "menu_catalog":  lambda: _handle_catalog(chat_id),
        "menu_payment":  lambda: _handle_payment_start(chat_id),
        "cart_done":   lambda: _handle_order_cart_done(chat_id),
        "cart_clear":  lambda: (clear_state(chat_id), _send(chat_id, t(chat_id,'order_cancelled_user')), _handle_menu(chat_id)),
        "cart_view":   lambda: _show_cart(chat_id),
        "order_place": lambda: _handle_order_place(chat_id),
        "order_cancel": lambda: (clear_state(chat_id), _send(chat_id, t(chat_id,'order_cancelled_user')), _handle_menu(chat_id)),
        "photo_receipt": lambda: (set_state(chat_id, photo_type='receipt'), _handle_photo_receipt_order(chat_id)),
        "menu_payment": lambda: _handle_payment_start(chat_id),
    }
    if data in cb_map:
        cb_map[data]()
        return

    if data.startswith("prod_") and not data.startswith("prod_photo_"):
        _handle_order_product_selected(chat_id, int(data.split("_")[1]))
    elif data.startswith("page_"):
        _handle_order_show_products(chat_id, int(data.split("_")[1]))
    elif data.startswith("confirm_order_"):
        _handle_confirm_order(chat_id, f"/tasdiqlash_{data.split('_')[2]}")
        _edit_inline(chat_id, msg_id, "", [])
    elif data.startswith("reject_order_"):
        _handle_reject_order(chat_id, f"/bekor_{data.split('_')[2]}")
        _edit_inline(chat_id, msg_id, "", [])
    elif data.startswith("receipt_order_"):
        order_pk = int(data.split("_")[2])
        set_state(chat_id, receipt_order_id=order_pk, step='waiting_photo')
        lang = get_lang(chat_id)
        _send(chat_id, "📸 Chek rasmini yuboring." if lang=='uz' else "📸 Фото чека.")
    elif data.startswith("pdf_order_"):
        _handle_send_pdf_by_id(chat_id, int(data.split("_")[2]))
    elif data.startswith("pay_order_"):
        _handle_payment_for_order(chat_id, f"/tolov_{data.split('_')[2]}")
    elif data.startswith("payme_"):
        _send_payme_link(chat_id, int(data.split("_")[1]))
    elif data.startswith("click_"):
        _send_click_link(chat_id, int(data.split("_")[1]))
    elif data.startswith("cash_pay_"):
        lang = get_lang(chat_id)
        _send(chat_id, "✅ Naqd to'lov. Yetkazishda to'laysiz." if lang=='uz' else "✅ Наличными при доставке.")
    elif data.startswith("reply_msg_"):
        _handle_reply_start(chat_id, f"/javob_{data.split('_')[2]}")


# ─── MENYU (REPLY KEYBOARD) ───────────────────────────────────────────

def _handle_menu(chat_id):
    from apps.users.models import User
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    lang = get_lang(chat_id)
    uz   = lang == 'uz'

    if not user:
        _send_inline(chat_id, "👋 <b>e-Mebel CRM</b>\n\nTilni tanlang:",
            [[{"text":"🇺🇿 O'zbekcha","callback_data":"lang_uz"},
              {"text":"🇷🇺 Русский",  "callback_data":"lang_ru"}]])
        return

    role = user.role
    if role == 'client':
        keyboard = [
            ["🛍 " + ("Buyurtma berish" if uz else "Оформить заказ"),
             "📦 " + ("Buyurtmalarim"   if uz else "Мои заказы")],
            ["💳 " + ("To'lov"          if uz else "Оплата"),
             "🛍 " + ("Katalog"         if uz else "Каталог")],
            ["💬 Chat", "❓ " + ("Yordam" if uz else "Помощь")],
        ]
    elif role == 'worker':
        keyboard = [
            ["🏭 " + ("Ombor"       if uz else "Склад"),
             "📦 " + ("Buyurtmalar" if uz else "Заказы")],
            ["💬 Chat", "❓ " + ("Yordam" if uz else "Помощь")],
        ]
    elif role == 'manager':
        keyboard = [
            ["📊 " + ("Statistika"  if uz else "Статистика"),
             "📦 " + ("Buyurtmalar" if uz else "Заказы")],
            ["🏭 " + ("Ombor"       if uz else "Склад"),
             "📊 " + ("Hisobot"     if uz else "Отчёт")],
            ["💬 Chat", "❓ " + ("Yordam" if uz else "Помощь")],
        ]
    elif role == 'admin':
        keyboard = [
            ["📊 " + ("Statistika"  if uz else "Статистика"), "📊 Dashboard"],
            ["📦 " + ("Buyurtmalar" if uz else "Заказы"), "🏭 " + ("Ombor" if uz else "Склад")],
            ["📊 " + ("Hisobot"     if uz else "Отчёт"), "🤖 AI Yordamchi"],
            ["💬 Chat", "❓ " + ("Yordam" if uz else "Помощь")],
        ]
    elif role == 'accountant':
        keyboard = [
            ["📊 " + ("Statistika"  if uz else "Статистика"),
             "📦 " + ("Buyurtmalar" if uz else "Заказы")],
            ["📊 " + ("Hisobot"     if uz else "Отчёт"), "💬 Chat"],
            ["❓ " + ("Yordam" if uz else "Помощь")],
        ]
    else:
        keyboard = [["❓ " + ("Yordam" if uz else "Помощь")]]

    greeting = f"📋 <b>{'Asosiy menyu' if uz else 'Главное меню'}</b>\n👇"
    _send_keyboard(chat_id, greeting, keyboard)


def _handle_start(chat_id, tg_username):
    from apps.users.models import User
    user = None
    if tg_username:
        user = User.objects.filter(telegram_username__iexact=tg_username).first()
    if not user:
        user = User.objects.filter(telegram_chat_id=chat_id).first()
    if user:
        user.telegram_chat_id = chat_id
        if tg_username: user.telegram_username = tg_username
        user.save(update_fields=["telegram_chat_id", "telegram_username"])
        roles = LANG[get_lang(chat_id)]['roles']
        _send(chat_id, t(chat_id, 'welcome_known', name=user.get_full_name() or user.username, role=roles.get(user.role, user.role)))
        _handle_menu(chat_id)
    else:
        _send_inline(chat_id, "👋 <b>e-Mebel CRM</b>\n\nTilni tanlang / Выберите язык:",
            [[{"text":"🇺🇿 O'zbekcha","callback_data":"lang_uz"},
              {"text":"🇷🇺 Русский",  "callback_data":"lang_ru"}]])


def _handle_after_lang(chat_id):
    from apps.users.models import User
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if user:
        _handle_menu(chat_id)
    else:
        lang = get_lang(chat_id)
        uz   = lang == 'uz'
        _send(chat_id,
            f"📋 CRM ga kiring → Admin → Users\nTelegram chat id: <code>{chat_id}</code>\n\n"
            f"{'Yoki /royxat' if uz else 'Или /register'}")


def _handle_lang_select(chat_id):
    _send_inline(chat_id, t(chat_id,'select_lang'),
        [[{"text":"🇺🇿 O'zbekcha","callback_data":"lang_uz"},
          {"text":"🇷🇺 Русский",  "callback_data":"lang_ru"}]])


# ─── KATALOG ──────────────────────────────────────────────────────────

def _handle_catalog(chat_id):
    from django.conf import settings
    webapp_url = getattr(settings, 'WEBAPP_URL', '')
    if webapp_url:
        lang = get_lang(chat_id)
        _send_inline(chat_id,
            "🛍 <b>Katalog</b>",
            [[{"text": t(chat_id,'catalog_btn'), "web_app": {"url": f"{webapp_url}/catalog"}}]])
    else:
        _handle_catalog_text(chat_id)


def _handle_catalog_text(chat_id):
    from apps.products.models import Product, Category
    from apps.warehouse.models import Stock
    lang = get_lang(chat_id)
    uz   = lang == 'uz'
    cats = Category.objects.prefetch_related('products').all()
    if not cats:
        _send(chat_id, "📭 Mahsulotlar yo'q." if uz else "📭 Товаров нет.")
        return
    text = "🛍 <b>" + ("Katalog" if uz else "Каталог") + "</b>\n━━━━━━━━━━━━━━━\n"
    for cat in cats:
        prods = Product.objects.filter(category=cat, is_active=True)
        if not prods: continue
        text += f"\n<b>📁 {cat.name}</b>\n"
        for p in prods:
            try:
                s = Stock.objects.get(product=p)
                av = f"✅{s.quantity}" if s.quantity > 0 else "❌"
            except: av = "❌"
            text += f"  • {p.name} — <b>{p.selling_price:,.0f}</b> [{av}]\n"
    text += "\n/buyurtma" if uz else "\n/order"
    if len(text) > 4000: text = text[:3900] + "..."
    _send(chat_id, text)


# ─── TO'LOV ───────────────────────────────────────────────────────────

def _handle_payment_start(chat_id):
    from apps.users.models import User
    from apps.orders.models import Order
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if not user or not user.client_profile:
        _send(chat_id, t(chat_id,'no_access')); return
    orders = Order.objects.filter(client=user.client_profile, payment_status__in=['unpaid','partial']).order_by('-created_at')[:5]
    lang = get_lang(chat_id); uz = lang == 'uz'
    if not orders:
        _send(chat_id, "✅ Barcha to'langan!" if uz else "✅ Все оплачено!"); return
    title = "💳 <b>" + ("To'lov kerak:" if uz else "К оплате:") + "</b>"
    buttons = [[{"text": f"#{o.order_number} — {o.remaining_amount:,.0f} so'm", "callback_data": f"pay_order_{o.pk}"}] for o in orders]
    _send_inline(chat_id, title, buttons)


def _handle_payment_for_order(chat_id, text):
    try: pk = int(text.split("_")[-1])
    except: return
    from apps.orders.models import Order
    try: order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        _send(chat_id, t(chat_id,'order_not_found')); return
    lang = get_lang(chat_id); uz = lang == 'uz'
    from django.conf import settings
    title = (f"💳 <b>#{order.order_number}</b>\n━━━\n"
             f"💰 {'Qoldiq' if uz else 'Остаток'}: <b>{order.remaining_amount:,.0f} so'm</b>\n\n"
             f"{'Usulni tanlang:' if uz else 'Выберите способ:'}")
    buttons = []
    if getattr(settings,'PAYME_MERCHANT_ID',''): buttons.append([{"text":"💳 Payme","callback_data":f"payme_{pk}"}])
    if getattr(settings,'CLICK_MERCHANT_ID',''): buttons.append([{"text":"💳 Click","callback_data":f"click_{pk}"}])
    buttons.append([{"text":"💵 "+("Naqd" if uz else "Наличные"),"callback_data":f"cash_pay_{pk}"}])
    buttons.append([{"text":"🧾 PDF","callback_data":f"pdf_order_{pk}"}])
    _send_inline(chat_id, title, buttons)


def _send_payme_link(chat_id, order_pk):
    from apps.orders.models import Order
    from .models import PaymeTransaction
    from django.conf import settings
    import base64
    try: order = Order.objects.get(pk=order_pk)
    except: _send(chat_id, t(chat_id,'order_not_found')); return
    merchant = getattr(settings,'PAYME_MERCHANT_ID','')
    amount   = int(order.remaining_amount * 100)
    is_test  = getattr(settings,'PAYME_TEST_MODE', True)
    base_url = "https://checkout.test.paycom.uz" if is_test else "https://checkout.paycom.uz"
    params   = f"m={merchant};ac.order_id={order.pk};a={amount};l={get_lang(chat_id)}"
    encoded  = base64.b64encode(params.encode()).decode()
    pay_url  = f"{base_url}/{encoded}"
    PaymeTransaction.objects.get_or_create(order=order, status='pending',
        defaults={'amount': order.remaining_amount, 'chat_id': chat_id})
    lang = get_lang(chat_id); uz = lang == 'uz'
    text = (f"💳 <b>Payme</b>\n━━━\n📋 #{order.order_number}\n"
            f"💰 {order.remaining_amount:,.0f} so'm")
    _send_inline(chat_id, text, [[{"text":"💳 "+("To'lash" if uz else "Оплатить"),"url":pay_url}]])
    _send(chat_id, t(chat_id,'pay_link_sent'))


def _send_click_link(chat_id, order_pk):
    from apps.orders.models import Order
    from .models import ClickTransaction
    from django.conf import settings
    try: order = Order.objects.get(pk=order_pk)
    except: _send(chat_id, t(chat_id,'order_not_found')); return
    merchant   = getattr(settings,'CLICK_MERCHANT_ID','')
    service_id = getattr(settings,'CLICK_SERVICE_ID','')
    amount     = int(order.remaining_amount)
    pay_url = (f"https://my.click.uz/services/pay?service_id={service_id}"
               f"&merchant_id={merchant}&amount={amount}&transaction_param={order.pk}")
    ClickTransaction.objects.get_or_create(order=order, status='pending',
        defaults={'amount': order.remaining_amount, 'chat_id': chat_id, 'merchant_trans_id': str(order.pk)})
    lang = get_lang(chat_id); uz = lang == 'uz'
    text = f"💳 <b>Click</b>\n━━━\n📋 #{order.order_number}\n💰 {order.remaining_amount:,.0f} so'm"
    _send_inline(chat_id, text, [[{"text":"💳 "+("To'lash" if uz else "Оплатить"),"url":pay_url}]])


# ─── BUYURTMA ─────────────────────────────────────────────────────────

def _handle_order_start(chat_id):
    from apps.users.models import User
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if not user or user.role != 'client':
        _send(chat_id, t(chat_id,'no_access')); return
    if not user.client_profile:
        lang = get_lang(chat_id)
        _send(chat_id, "❌ Mijoz profili yo'q." if lang=='uz' else "❌ Профиль не найден."); return
    clear_state(chat_id)
    set_state(chat_id, step='selecting_products')
    get_session(chat_id).set_cart([])
    _handle_order_show_products(chat_id, page=0)


def _handle_order_show_products(chat_id, page=0):
    from apps.products.models import Product
    from apps.warehouse.models import Stock
    PAGE_SIZE = 6
    products = list(Product.objects.filter(is_active=True).order_by('category','name'))
    total    = len(products)
    page_ps  = products[page*PAGE_SIZE:(page+1)*PAGE_SIZE]
    if not page_ps:
        _send(chat_id, "📭"); return
    lang = get_lang(chat_id); uz = lang=='uz'
    text = t(chat_id,'order_step1') + "\n"
    for p in page_ps:
        try:
            s = Stock.objects.get(product=p)
            qi = f"({s.quantity} {'dona' if uz else 'шт.'})" if s.quantity>0 else "❌"
        except: qi = "(0)"
        text += f"\n• <b>{p.name}</b> — {p.selling_price:,.0f} so'm {qi}"
    buttons = []
    row = []
    for i, p in enumerate(page_ps):
        row.append({"text": f"🛒 {p.name[:20]}", "callback_data": f"prod_{p.pk}"})
        if len(row) == 2: buttons.append(row); row = []
    if row: buttons.append(row)
    nav = []
    if page > 0: nav.append({"text":"⬅️","callback_data":f"page_{page-1}"})
    if (page+1)*PAGE_SIZE < total: nav.append({"text":"➡️","callback_data":f"page_{page+1}"})
    if nav: buttons.append(nav)
    cart = get_session(chat_id).get_cart()
    action = []
    if cart:
        action.append({"text":f"🛒 {'Savat' if uz else 'Корзина'}({len(cart)})","callback_data":"cart_view"})
        action.append({"text":"✅ "+("Buyurtma" if uz else "Оформить"),"callback_data":"cart_done"})
    else:
        action.append({"text":"❌ "+("Bekor" if uz else "Отмена"),"callback_data":"cart_clear"})
    buttons.append(action)
    set_state(chat_id, current_page=page)
    _send_inline(chat_id, text, buttons)


def _handle_order_product_selected(chat_id, product_id):
    from apps.products.models import Product
    try: product = Product.objects.get(pk=product_id, is_active=True)
    except: _send(chat_id, t(chat_id,'order_not_found')); return
    set_state(chat_id, step='waiting_qty', selected_product_id=product_id)
    _send(chat_id, t(chat_id,'order_qty_ask', name=product.name, price=float(product.selling_price)))


def _handle_order_qty(chat_id, text):
    try:
        qty = int(text.strip())
        if qty < 1 or qty > 100: raise ValueError
    except ValueError:
        _send(chat_id, t(chat_id,'order_invalid_qty')); return
    state = get_state(chat_id)
    product_id = state.get('selected_product_id')
    if not product_id: _handle_order_start(chat_id); return
    from apps.products.models import Product
    from apps.warehouse.models import Stock
    try:
        product = Product.objects.get(pk=product_id)
        stock   = Stock.objects.get(product=product)
        if qty > stock.quantity:
            lang = get_lang(chat_id)
            _send(chat_id, f"❌ Omborda {stock.quantity} ta!" if lang=='uz' else f"❌ На складе {stock.quantity} шт.!"); return
    except Exception:
        _send(chat_id, t(chat_id,'order_not_found')); return
    session = get_session(chat_id)
    session.add_to_cart(product_id, product.name, float(product.selling_price), qty)
    set_state(chat_id, step='selecting_products')
    _send(chat_id, t(chat_id,'order_cart_add', name=product.name, qty=qty))
    _handle_order_show_products(chat_id, page=state.get('current_page',0))


def _show_cart(chat_id):
    cart = get_session(chat_id).get_cart()
    if not cart: _send(chat_id, t(chat_id,'order_cart_empty')); return
    lang = get_lang(chat_id); uz = lang=='uz'
    total = sum(i['price']*i['qty'] for i in cart)
    lines = "\n".join(f"  • {i['name']} × {i['qty']} = {i['price']*i['qty']:,.0f}" for i in cart)
    text  = f"🛒 <b>{'Savat' if uz else 'Корзина'}:</b>\n{lines}\n━━━━━━━━\n💰 <b>{total:,.0f} so'm</b>"
    buttons = [[{"text":"✅ "+("Davom" if uz else "Продолжить"),"callback_data":"cart_done"},
                {"text":"❌ "+("Bekor" if uz else "Отмена"),"callback_data":"cart_clear"}]]
    _send_inline(chat_id, text, buttons)


def _handle_order_cart_done(chat_id):
    if not get_session(chat_id).get_cart():
        _send(chat_id, t(chat_id,'order_cart_empty')); return
    set_state(chat_id, step='waiting_address')
    _send(chat_id, t(chat_id,'order_address_ask'))


def _handle_order_address(chat_id, address):
    if len(address.strip()) < 5:
        lang = get_lang(chat_id)
        _send(chat_id, "❌ Manzil qisqa." if lang=='uz' else "❌ Адрес короткий."); return
    session = get_session(chat_id)
    cart    = session.get_cart()
    set_state(chat_id, address=address.strip(), step='confirm')
    total = sum(i['price']*i['qty'] for i in cart)
    lines = "\n".join(f"  • {i['name']} × {i['qty']} — {i['price']*i['qty']:,.0f} so'm" for i in cart)
    lang = get_lang(chat_id); uz = lang=='uz'
    text = t(chat_id,'order_confirm_text', items=lines, total=total, address=address.strip())
    buttons = [[{"text":"✅ "+("Ha" if uz else "Да"),"callback_data":"order_place"},
                {"text":"❌ "+("Bekor" if uz else "Отмена"),"callback_data":"order_cancel"}]]
    _send_inline(chat_id, text, buttons)


def _handle_order_place(chat_id):
    from apps.users.models import User
    from apps.orders.models import Order, OrderItem
    from apps.warehouse.models import Stock
    from apps.products.models import Product
    from decimal import Decimal
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if not user or not user.client_profile:
        _send(chat_id, t(chat_id,'no_access')); return
    session = get_session(chat_id)
    cart    = session.get_cart()
    address = session.data.get('address','')
    if not cart or not address:
        _send(chat_id, t(chat_id,'order_cart_empty')); return
    items_data = []
    for item in cart:
        try:
            p = Product.objects.get(pk=item['product_id'], is_active=True)
            s = Stock.objects.get(product=p)
            if s.quantity < item['qty']:
                lang = get_lang(chat_id)
                _send(chat_id, f"❌ {p.name}: {s.quantity} {'dona' if lang=='uz' else 'шт.'}!"); return
            items_data.append({'product':p,'qty':item['qty'],'price':Decimal(str(item['price']))})
        except Exception as e:
            logger.error(f"Order: {e}"); continue
    if not items_data:
        _send(chat_id, t(chat_id,'order_not_found')); return
    order = Order.objects.create(client=user.client_profile, status='new', delivery_address=address, notes='Telegram')
    total = Decimal('0')
    for item in items_data:
        OrderItem.objects.create(order=order, product=item['product'], quantity=item['qty'], price=item['price'])
        total += item['price'] * item['qty']
    order.total_amount = total
    order.save()
    clear_state(chat_id)
    lang = get_lang(chat_id); uz = lang=='uz'
    _send(chat_id, t(chat_id,'order_placed', num=order.order_number))
    buttons = [
        [{"text":"💳 "+("To'lov" if uz else "Оплата"),"callback_data":f"pay_order_{order.pk}"}],
        [{"text":"🧾 PDF","callback_data":f"pdf_order_{order.pk}"}],
    ]
    _send_inline(chat_id, "🎉", buttons)
    try:
        from .notify import notify_new_order
        notify_new_order(order)
    except Exception as e:
        logger.error(f"Notify: {e}")
    try:
        from .tasks import schedule_order_reminders
        schedule_order_reminders.delay(order.pk)
    except Exception: pass


# ─── WORKER ───────────────────────────────────────────────────────────

def _handle_confirm_order(chat_id, text):
    from apps.users.models import User
    from apps.orders.models import Order
    from apps.warehouse.models import Stock, StockMovement
    from django.db import transaction
    user = get_user(chat_id)
    if not is_staff(user): _send(chat_id, t(chat_id,'no_access')); return
    try:
        pk = int(text.split("_")[-1])
        order = Order.objects.get(pk=pk)
    except Exception:
        _send(chat_id, t(chat_id,'order_not_found')); return
    if order.status != "new":
        _send(chat_id, t(chat_id,'already_processed', num=order.order_number, status=order.status)); return
    insufficient = []
    for item in order.items.select_related("product"):
        try:
            s = Stock.objects.get(product=item.product)
            if s.quantity < item.quantity: insufficient.append(f"  • {item.product.name}: {item.quantity}/{s.quantity}")
        except Stock.DoesNotExist: insufficient.append(f"  • {item.product.name}: yo'q")
    if insufficient:
        _send(chat_id, t(chat_id,'no_stock', items="\n".join(insufficient))); return
    with transaction.atomic():
        for item in order.items.select_related("product"):
            StockMovement.objects.create(product=item.product, movement_type="out",
                quantity=item.quantity, reason=f"#{order.order_number} Telegram", performed_by=user)
        order.status = "production"; order.save()
    _send(chat_id, t(chat_id,'confirmed', num=order.order_number))
    try:
        from .notify import notify_order_confirmed
        notify_order_confirmed(order)
    except Exception as e: logger.error(f"Notify: {e}")


def _handle_reject_order(chat_id, text):
    from apps.users.models import User
    from apps.orders.models import Order
    user = get_user(chat_id)
    if not is_staff(user): _send(chat_id, t(chat_id,'no_access')); return
    try:
        pk = int(text.split("_")[-1])
        order = Order.objects.get(pk=pk, status="new")
    except Exception:
        _send(chat_id, t(chat_id,'order_not_found')); return
    order.status = "cancelled"; order.save()
    _send(chat_id, t(chat_id,'cancelled_order', num=order.order_number))
    try:
        from .notify import notify_order_cancelled
        notify_order_cancelled(order)
    except Exception: pass


def _handle_order_status(chat_id, text):
    from apps.orders.models import Order
    user = get_user(chat_id)
    if not user: _send(chat_id, t(chat_id,'not_linked')); return
    try:
        pk = int(text.split("_")[-1])
        order = Order.objects.get(pk=pk, client=user.client_profile) if user.role=='client' and user.client_profile else Order.objects.get(pk=pk)
    except Exception:
        _send(chat_id, t(chat_id,'order_not_found')); return
    lang = get_lang(chat_id); uz = lang=='uz'
    st_emoji = {"new":"🆕","pending":"⚙️","production":"🏭","ready":"📦","delivered":"🚚","completed":"✅","cancelled":"❌"}
    text_out = (
        f"📋 <b>#{order.order_number}</b>\n━━━\n"
        f"{st_emoji.get(order.status,'📋')} <b>{order.get_status_display()}</b>\n"
        f"💰 {order.total_amount:,.0f} | ⏳ {order.remaining_amount:,.0f} so'm"
    )
    buttons = [[{"text":"💳 "+("To'lov" if uz else "Оплата"),"callback_data":f"pay_order_{order.pk}"},
                {"text":"🧾 PDF","callback_data":f"pdf_order_{order.pk}"}]]
    _send_inline(chat_id, text_out, buttons)


def _handle_my_orders(chat_id):
    from apps.orders.models import Order
    user = get_user(chat_id)
    if not user: _send(chat_id, t(chat_id,'not_linked')); return
    lang = get_lang(chat_id); uz = lang=='uz'
    if user.role == "client" and user.client_profile:
        orders = Order.objects.filter(client=user.client_profile).order_by("-created_at")[:5]
    elif is_staff(user):
        orders = Order.objects.all().order_by("-created_at")[:10]
    else:
        _send(chat_id, t(chat_id,'no_access')); return
    if not orders: _send(chat_id, t(chat_id,'no_orders')); return
    st_emoji = {"new":"🆕","pending":"⚙️","production":"🏭","ready":"📦","delivered":"🚚","completed":"✅","cancelled":"❌"}
    text = t(chat_id,'orders_title'); buttons = []
    for o in orders:
        text += f"{st_emoji.get(o.status,'📋')} #{o.order_number} — {o.get_status_display()}\n"
        text += f"   💰{o.total_amount:,.0f} | ⏳{o.remaining_amount:,.0f}\n\n"
        if is_staff(user) and o.status == 'new':
            buttons.append([{"text":f"✅#{o.order_number}","callback_data":f"confirm_order_{o.pk}"},
                            {"text":f"❌#{o.order_number}","callback_data":f"reject_order_{o.pk}"}])
        elif user.role == 'client':
            buttons.append([{"text":f"💳#{o.order_number}","callback_data":f"pay_order_{o.pk}"},
                            {"text":f"🧾PDF","callback_data":f"pdf_order_{o.pk}"}])
    _send_inline(chat_id, text, buttons) if buttons else _send(chat_id, text)


# ─── STATISTIKA ───────────────────────────────────────────────────────

def _handle_statistics(chat_id):
    user = get_user(chat_id)
    if not is_admin_or_manager(user):
        _send(chat_id, t(chat_id,'no_access')); return
    from apps.orders.models import Order
    from apps.clients.models import Client
    from django.db.models import Sum, Count
    from django.utils import timezone
    from datetime import timedelta
    today    = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago= today - timedelta(days=30)
    total_orders  = Order.objects.count()
    today_orders  = Order.objects.filter(created_at__date=today).count()
    week_orders   = Order.objects.filter(created_at__date__gte=week_ago).count()
    month_revenue = Order.objects.filter(created_at__date__gte=month_ago).aggregate(s=Sum('paid_amount'))['s'] or 0
    total_revenue = Order.objects.aggregate(s=Sum('paid_amount'))['s'] or 0
    total_clients = Client.objects.count()
    sc = dict(Order.objects.values('status').annotate(c=Count('id')).values_list('status','c'))
    lang = get_lang(chat_id); uz = lang=='uz'
    text = (
        f"📊 <b>Statistika</b>\n━━━\n"
        f"📅 {'Bugun' if uz else 'Сегодня'}: {today_orders} | "
        f"{'Hafta' if uz else 'Неделя'}: {week_orders} | "
        f"{'Jami' if uz else 'Всего'}: {total_orders}\n"
        f"💰 {'Oy' if uz else 'Месяц'}: {month_revenue:,.0f} | "
        f"{'Jami' if uz else 'Итого'}: {total_revenue:,.0f} so'm\n"
        f"👥 {'Mijozlar' if uz else 'Клиентов'}: {total_clients}\n━━━\n"
    )
    for st, em in [('new','🆕'),('production','🏭'),('ready','📦'),('delivered','🚚'),('cancelled','❌')]:
        if sc.get(st): text += f"{em} {st}: {sc[st]}\n"
    _send(chat_id, text)


# ─── OMBOR ────────────────────────────────────────────────────────────

def _handle_stock(chat_id):
    from apps.users.models import User
    from apps.warehouse.models import Stock
    user = get_user(chat_id)
    if not is_staff(user): _send(chat_id, t(chat_id,'no_access')); return
    stocks = Stock.objects.select_related("product").order_by("quantity")[:20]
    if not stocks: _send(chat_id, t(chat_id,'stock_empty')); return
    lang = get_lang(chat_id); uz = lang=='uz'
    text = t(chat_id,'stock_title')
    for s in stocks:
        icon = "🔴" if s.quantity==0 else ("🟡" if s.is_low else "🟢")
        text += f"{icon} {s.product.name}: <b>{s.quantity} {'dona' if uz else 'шт.'}</b>\n"
    _send(chat_id, text)


def _handle_report(chat_id):
    from apps.users.models import User
    user = get_user(chat_id)
    if not is_management(user): _send(chat_id, t(chat_id,'no_access')); return
    from .notify import send_daily_report
    send_daily_report()


# ─── CHAT ─────────────────────────────────────────────────────────────

def _handle_chat_start(chat_id):
    user = get_user(chat_id)
    if not user: _send(chat_id, t(chat_id,'not_linked')); return
    set_state(chat_id, step='waiting_chat_message')
    _send(chat_id, t(chat_id,'chat_send'))


def _handle_chat_send(chat_id, text):
    from apps.users.models import User, Message
    user = get_user(chat_id)
    if not user: clear_state(chat_id); return
    for acc in User.objects.filter(role__in=['accountant','admin'], is_active=True):
        Message.objects.create(sender=user, receiver=acc, body=f"[Telegram]: {text}")
        if acc.telegram_chat_id:
            _send(acc.telegram_chat_id, f"💬 <b>{user.get_full_name() or user.username}:</b>\n{text}\n\n/javob_{user.pk}")
    _send(chat_id, t(chat_id,'chat_sent'))
    clear_state(chat_id); _handle_menu(chat_id)


def _handle_reply_start(chat_id, text):
    user = get_user(chat_id)
    if not is_management(user):
        _send(chat_id, t(chat_id,'no_access')); return
    try: target_id = int(text.split("_")[-1])
    except: _send(chat_id, "❌ Format"); return
    set_state(chat_id, step='waiting_reply_message', reply_to_user_id=target_id)
    lang = get_lang(chat_id)
    _send(chat_id, "💬 Javob yozing:" if lang=='uz' else "💬 Напишите ответ:")


def _handle_chat_reply(chat_id, text):
    from apps.users.models import User, Message
    user = get_user(chat_id)
    if not user: clear_state(chat_id); return
    state = get_state(chat_id)
    try:
        target = User.objects.get(pk=state.get('reply_to_user_id'))
        Message.objects.create(sender=user, receiver=target, body=f"[Javob]: {text}")
        if target.telegram_chat_id:
            _send(target.telegram_chat_id, f"💬 <b>{user.get_full_name() or user.username}:</b>\n{text}")
        _send(chat_id, t(chat_id,'chat_reply'))
    except User.DoesNotExist:
        _send(chat_id, "❌ Foydalanuvchi topilmadi.")
    clear_state(chat_id); _handle_menu(chat_id)


# ─── RO'YXAT ──────────────────────────────────────────────────────────

def _handle_register_start(chat_id):
    from apps.users.models import User
    if User.objects.filter(telegram_chat_id=chat_id).exists():
        _send(chat_id, t(chat_id,'register_exists')); _handle_menu(chat_id); return
    set_state(chat_id, step='register_name')
    _send(chat_id, t(chat_id,'register_name'))


def _handle_register_name(chat_id, text):
    if len(text.strip()) < 3:
        lang = get_lang(chat_id)
        _send(chat_id, "❌ Ism qisqa." if lang=='uz' else "❌ Имя короткое."); return
    set_state(chat_id, step='register_phone', reg_name=text.strip())
    _send(chat_id, t(chat_id,'register_phone'))


def _handle_register_phone(chat_id, text):
    import re
    phone = text.strip().replace(' ','').replace('-','')
    if not re.match(r'^\+?998\d{9}$', phone):
        _send(chat_id, "❌ +998901234567"); return
    state = get_state(chat_id)
    name  = state.get('reg_name','')
    try:
        from apps.clients.models import Client
        from .notify import _send_to_roles
        if Client.objects.filter(phone=phone).exists():
            lang = get_lang(chat_id)
            _send(chat_id, "ℹ️ Allaqachon ro'yxatdan o'tgan." if lang=='uz' else "ℹ️ Уже зарегистрирован.")
            clear_state(chat_id); return
        Client.objects.create(name=name, phone=phone)
        _send_to_roles("admin","manager", text=f"👤 Yangi mijoz!\nIsm: {name}\nTel: {phone}\nTG: {chat_id}")
        _send(chat_id, t(chat_id,'register_done', name=name, phone=phone))
        clear_state(chat_id); _handle_menu(chat_id)
    except Exception as e:
        logger.error(f"Register: {e}")
        _send(chat_id, "❌ Xato."); clear_state(chat_id)


# ─── RASM ─────────────────────────────────────────────────────────────

def _handle_photo(chat_id, message):
    """
    Rasm qabul qilinganda:
    1. Barcode/QR kod skanerlash (opencv)
    2. To'lov cheki sifatida saqlash
    """
    user = get_user(chat_id)
    if not user: _send(chat_id, t(chat_id, 'not_linked')); return

    photos  = message.get("photo", [])
    if not photos: return
    file_id = photos[-1]["file_id"]   # Eng katta o'lcham
    state   = get_state(chat_id)
    lang    = get_lang(chat_id)
    uz      = lang == 'uz'

    # ── Barcode/QR aniqlash ─────────────────────────────────────────
    if SCANNER_AVAILABLE and state.get('step') not in ('waiting_photo',):
        img_bytes = download_photo_bytes(file_id)
        if img_bytes:
            code = decode_barcode_from_bytes(img_bytes)
            if code:
                _send(chat_id, f"🔍 <b>Barcode:</b> <code>{code}</code>")
                # Mahsulotni SKU yoki barcode orqali qidirish
                from apps.products.models import Product
                from apps.warehouse.models import Stock
                product = (
                    Product.objects.filter(sku__iexact=code, is_active=True).first() or
                    Product.objects.filter(name__iexact=code, is_active=True).first()
                )
                if product:
                    try:
                        stock = Stock.objects.get(product=product)
                        qty_txt = f"{stock.quantity} {'dona' if uz else 'шт.'}"
                        status  = "✅" if stock.quantity > 0 else "❌"
                    except Stock.DoesNotExist:
                        qty_txt = "0"
                        status  = "❌"
                    text = (
                        f"📦 <b>{product.name}</b>\n"
                        f"🏷 SKU: <code>{product.sku}</code>\n"
                        f"💰 {'Narxi' if uz else 'Цена'}: <b>{product.selling_price:,.0f} so'm</b>\n"
                        f"{status} {'Ombor' if uz else 'Склад'}: {qty_txt}"
                    )
                    buttons = []
                    if user.role == 'client':
                        buttons = [[{"text": f"🛒 {'Savatga' if uz else 'В корзину'}", "callback_data": f"prod_{product.pk}"}]]
                    _send_inline(chat_id, text, buttons) if buttons else _send(chat_id, text)
                else:
                    _send(chat_id, f"❌ <code>{code}</code> — {'mahsulot topilmadi' if uz else 'товар не найден'}")
                return  # Barcode topildi, chek qismiga o'tmaymiz

    # ── To'lov cheki / AI Fallback ──────────────────────────────────
    photo_type = state.get('photo_type')
    step       = state.get('step')
    if photo_type == 'receipt' or step == 'waiting_photo':
        order_id = state.get('receipt_order_id')
        if not order_id:
            _handle_photo_receipt_order(chat_id)
            return
        _save_payment_receipt_photo(chat_id, user, file_id, order_id)
    elif is_staff(user):
        # Xodimlar uchun AI dan yordam so'rash
        _send(chat_id, "🔍 <b>Rasmda shtrix-kod aniqlanmadi.</b>\nIltimos, rasmni yaqinroq va aniqroq tushirib yuboring.")
    else:
        set_state(chat_id, last_photo_file_id=file_id)
        _send_inline(chat_id, t(chat_id, 'photo_received'),
            [[{"text": "💳 " + ("To'lov cheki" if uz else "Чек оплаты"), "callback_data": "photo_receipt"}]])


def _handle_photo_receipt_order(chat_id):
    from apps.users.models import User
    from apps.orders.models import Order
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if not user or not user.client_profile: return
    orders = Order.objects.filter(client=user.client_profile, payment_status__in=['unpaid','partial']).order_by('-created_at')[:5]
    if not orders:
        lang = get_lang(chat_id)
        _send(chat_id, "📭 To'lanmagan yo'q." if lang=='uz' else "📭 Нет неоплаченных."); return
    lang = get_lang(chat_id)
    title = "🧾 Qaysi buyurtma?" if lang=='uz' else "🧾 Для какого заказа?"
    buttons = [[{"text":f"#{o.order_number} — {o.remaining_amount:,.0f}","callback_data":f"receipt_order_{o.pk}"}] for o in orders]
    _send_inline(chat_id, title, buttons)


def _save_payment_receipt_photo(chat_id, user, file_id, order_id):
    from apps.orders.models import Order, Payment
    try:
        order = Order.objects.get(pk=order_id)
        Payment.objects.create(order=order, amount=order.remaining_amount, method='transfer',
            note=f"Telegram chek ({file_id})", submitted_by=user, is_confirmed=False)
        _send(chat_id, t(chat_id,'receipt_saved'))
        clear_state(chat_id)
        from apps.users.models import User as U
        for acc in U.objects.filter(role__in=['accountant','admin'], is_active=True).exclude(telegram_chat_id=''):
            _send_photo(acc.telegram_chat_id, file_id,
                caption=f"🧾 #{order.order_number} — {order.client.name}\n{order.remaining_amount:,.0f} so'm")
    except Exception as e:
        logger.error(f"Receipt: {e}")
        _send(chat_id, "❌ Xato.")


# ─── LOKATSIYA ────────────────────────────────────────────────────────

def _handle_location(chat_id, location):
    from apps.users.models import User
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if not user: _send(chat_id, t(chat_id,'not_linked')); return
    lat = location.get('latitude'); lon = location.get('longitude')
    step = get_state(chat_id).get('step')
    if step == 'waiting_address':
        _handle_order_address(chat_id, f"📍 GPS: {lat}, {lon}"); return
    lang = get_lang(chat_id); uz = lang=='uz'
    _send(chat_id, f"📍 https://maps.google.com/?q={lat},{lon}")
    if user.role == 'client' and user.client_profile:
        from apps.orders.models import Order
        last = Order.objects.filter(client=user.client_profile, status__in=['new','pending']).order_by('-created_at').first()
        if last:
            last.delivery_address = f"GPS: {lat}, {lon}"; last.save()
            _send(chat_id, f"✅ #{last.order_number} — {'manzil saqlandi' if uz else 'адрес сохранён'}")


def _handle_document(chat_id, message):
    lang = get_lang(chat_id); uz = lang=='uz'
    doc  = message.get("document",{})
    _send(chat_id, f"📄 {'Fayl qabul qilindi' if uz else 'Файл получен'}: {doc.get('file_name','')}")


# ─── PDF ──────────────────────────────────────────────────────────────

def _handle_send_pdf_receipt(chat_id, text):
    try: pk = int(text.split("_")[-1])
    except: _send(chat_id, "❌ /chek_15"); return
    _handle_send_pdf_by_id(chat_id, pk)


def _handle_send_pdf_by_id(chat_id, order_pk):
    from apps.orders.models import Order
    from apps.users.models import User
    user = User.objects.filter(telegram_chat_id=chat_id).first()
    if not user: _send(chat_id, t(chat_id,'not_linked')); return
    try:
        order = Order.objects.get(pk=order_pk, client=user.client_profile) if user.role=='client' and user.client_profile else Order.objects.get(pk=order_pk)
    except Order.DoesNotExist:
        _send(chat_id, t(chat_id,'order_not_found')); return
    _send(chat_id, t(chat_id,'pdf_preparing'))
    try:
        from .pdf_generator import generate_order_pdf
        pdf_bytes = generate_order_pdf(order)
        _send_document(chat_id, pdf_bytes, f"buyurtma_{order.order_number}.pdf", caption=f"🧾 #{order.order_number}")
    except Exception as e:
        logger.error(f"PDF: {e}")
        _send_text_receipt(chat_id, order)


def _send_text_receipt(chat_id, order):
    lang = get_lang(chat_id); uz = lang=='uz'
    items = "\n".join(f"  • {i.product.name}×{i.quantity}={i.subtotal:,.0f}" for i in order.items.select_related('product').all())
    text  = (
        f"🧾 <b>#{order.order_number}</b>\n━━━\n"
        f"👤 {order.client.name}\n{items}\n━━━\n"
        f"💰 {order.total_amount:,.0f} | ✅ {order.paid_amount:,.0f} | ⏳ {order.remaining_amount:,.0f} so'm"
    )
    _send(chat_id, text)


# ─── YORDAM ───────────────────────────────────────────────────────────

def _handle_help(chat_id):
    from apps.users.models import User
    try:
        user = User.objects.filter(telegram_chat_id=str(chat_id)).first()
        lang = get_lang(chat_id); uz = lang=='uz'
        
        if not user:
            _send(chat_id, "👋 <b>e-Mebel CRM</b>\n\n/start - Ishga tushirish\n/royxat - Ro'yxatdan o'tish" if uz else 
                           "👋 <b>e-Mebel CRM</b>\n\n/start - Запустить\n/register - Регистрация")
            return

        base = f"📖 <b>{'Buyruqlar' if uz else 'Команды'}:</b>\n\n"
        base += "🏠 /menyu - Asosiy menyu\n"
        base += "🌐 /til - Tilni o'zgartirish\n"
        base += "🛍 /katalog - Katalog (WebApp)\n"
        
        if user.role == 'client':
            base += "🛍 /buyurtma - Yangi buyurtma\n"
            base += "📦 /buyurtmalar - Buyurtmalarim\n"
        elif user.role in ('worker', 'admin', 'manager'):
            base += "🏭 /ombor - Ombor holati\n"
            if user.role != 'worker':
                base += "📊 /statistika - Savdo statistikasi\n"
                base += "📊 /dashboard - Grafik dashboard\n"
                base += "📢 /broadcast - Xabar yuborish\n"
        
        base += "🤖 /ai - AI Yordamchi\n"
        _send(chat_id, base)
    except Exception as e:
        logger.error(f"Help error: {e}")
        _send(chat_id, "❌ Xatolik yuz berdi. /start bosib ko'ring.")


# ── Dashboard & AI ────────────────────────────────────────────────────

def _handle_dashboard(chat_id):
    user = get_user(chat_id)
    if not is_admin_or_manager(user):
        _send(chat_id, t(chat_id,'no_access')); return
    _send(chat_id, "📊 <b>Dashboard yuklanmoqda...</b>")
    try:
        send_visual_report(chat_id)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        _send(chat_id, "❌ Grafik yuklashda xato.")


def _handle_ai_start(chat_id):
    lang = get_lang(chat_id)
    msg = "🤖 <b>AI Yordamchi</b>\n\nMen CRM ma'lumotlari bo'yicha savollaringizga javob beraman. Masalan:\n- Bugun qancha buyurtma bo'ldi?\n- Qaysi mahsulotlar tugayapti?\n- Oxirgi buyurtmalar qanaqa?"
    _send(chat_id, msg)


def _handle_unknown_text(chat_id, text):
    user = get_user(chat_id)
    # Faqat xodimlar AI dan foydalana oladi
    if is_staff(user):
        _send(chat_id, "🤖 <i>AI o'ylamoqda...</i>")
        try:
            response = get_ai_response(text, chat_id)
            _send(chat_id, response)
        except Exception as e:
            logger.error(f"AI error: {e}")
            _send(chat_id, "❌ AI hozirda band.")
    else:
        _handle_menu(chat_id)


def _handle_broadcast(chat_id, text):
    from apps.users.models import User
    user = User.objects.filter(telegram_chat_id=chat_id, role='admin').first()
    if not user:
        _send(chat_id, t(chat_id,'no_access')); return
    
    msg_body = text.replace("/broadcast ", "").strip()
    if not msg_body or msg_body == "/broadcast":
        _send(chat_id, "❌ Xabar matnini yozing: /broadcast <matn>"); return

    staff = User.objects.filter(role__in=['admin','manager','worker','accountant']).exclude(telegram_chat_id='')
    sent_count = 0
    for s in staff:
        if s.telegram_chat_id == chat_id: continue
        if _send(s.telegram_chat_id, f"📢 <b>Xizmat xabari:</b>\n{msg_body}"):
            sent_count += 1
    
    _send(chat_id, f"✅ {sent_count} ta xodimga xabar yuborildi.")


# ─── ESLATMALAR ───────────────────────────────────────────────────────

def _handle_check_reminders():
    from apps.orders.models import Order
    from django.utils import timezone
    from datetime import timedelta
    tomorrow = timezone.now().date() + timedelta(days=1)
    orders = Order.objects.filter(delivery_date=tomorrow, status__in=['production','ready','pending']).select_related('client','manager')
    for order in orders:
        if order.manager and order.manager.telegram_chat_id:
            lang = get_lang(order.manager.telegram_chat_id); uz = lang=='uz'
            _send(order.manager.telegram_chat_id,
                f"🔔 <b>{'Ertaga yetkazish' if uz else 'Завтра доставка'}!</b>\n"
                f"#{order.order_number} — {order.client.name}\n"
                f"📞 {order.client.phone}\n"
                f"💰 {'Qoldiq' if uz else 'Остаток'}: {order.remaining_amount:,.0f} so'm")