from django.urls import path
from django.conf import settings
from . import bot

token = getattr(settings, "TELEGRAM_BOT_TOKEN", "TOKEN")

urlpatterns = [
    # Telegram webhook — URL da token bor, xavfsizlik uchun
    path(f"telegram/webhook/{token}/", bot.telegram_webhook, name="telegram_webhook"),
]
