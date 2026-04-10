#!/usr/bin/env python
"""
run_bot_polling.py — Telegram botni polling rejimida ishga tushirish
Localhost da webhook ishlamasa, shu faylni ishlatib ko'ring.

Ishlatish:
    python run_bot_polling.py

Bu fayl merged/ papkasiga qo'yilishi kerak (manage.py bilan bir joyda).
"""
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import time
import logging
import requests
import django

# Django sozlash
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from django.conf import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

TOKEN = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN .env faylda topilmadi!")
    print("   .env faylga qo'shing: TELEGRAM_BOT_TOKEN=sizning_tokeningiz")
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


def delete_webhook():
    """Avval webhookni o'chiramiz (polling bilan webhook birgalikda ishlamaydi)."""
    resp = requests.post(f"{BASE_URL}/deleteWebhook", timeout=10)
    if resp.ok:
        logger.info("✅ Webhook o'chirildi, polling boshlanyapti...")
    else:
        logger.warning(f"Webhook o'chirishda xato: {resp.text}")


def get_updates(offset=None, timeout=30):
    """Yangi xabarlarni olish."""
    params = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
    if offset:
        params["offset"] = offset
    try:
        resp = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=timeout + 5)
        if resp.ok:
            return resp.json().get("result", [])
    except requests.exceptions.ReadTimeout:
        pass
    except Exception as e:
        logger.error(f"getUpdates xato: {e}")
        time.sleep(3)
    return []


def process_update(update):
    """Har bir updateni bot.py orqali ishlab chiqish."""
    try:
        from apps.telegram_bot.bot import telegram_webhook
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.post(
            '/telegram/webhook/',
            data=json.dumps(update),
            content_type='application/json'
        )
        telegram_webhook(request)
    except Exception as e:
        logger.error(f"Update ishlab chiqishda xato: {e}", exc_info=True)


def main():
    print("=" * 50)
    print("  🤖 e-Mebel CRM Telegram Bot")
    print("  📡 Polling rejimi (localhost)")
    print("=" * 50)

    delete_webhook()

    # Bot ma'lumotlarini tekshirish
    try:
        resp = requests.get(f"{BASE_URL}/getMe", timeout=10)
        if resp.ok:
            bot_info = resp.json().get("result", {})
            print(f"  ✅ Bot: @{bot_info.get('username')} ({bot_info.get('first_name')})")
        else:
            print(f"  ❌ Token noto'g'ri: {resp.text}")
            sys.exit(1)
    except Exception as e:
        print(f"  ❌ Telegram ulanishda xato: {e}")
        sys.exit(1)

    print("  🟢 Xabarlar kutilmoqda...")
    print("  Toxtatish uchun: Ctrl+C")
    print("=" * 50)

    offset = None
    while True:
        try:
            updates = get_updates(offset=offset)
            for update in updates:
                update_id = update.get("update_id")
                logger.info(f"📨 Update #{update_id} keldi")
                process_update(update)
                offset = update_id + 1
        except KeyboardInterrupt:
            print("\n\n  👋 Bot to'xtatildi.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Asosiy tsiklda xato: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()