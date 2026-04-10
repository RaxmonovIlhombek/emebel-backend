import requests
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = "Telegram webhook o'rnatish"
    def add_arguments(self, parser):
        parser.add_argument("url", help="Server URL, masalan: https://yourdomain.com")

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        server_url = options["url"].rstrip("/")
        webhook_url = f"{server_url}/telegram/webhook/{token}/"
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/setWebhook",
            json={"url": webhook_url}
        )
        if resp.ok and resp.json().get("ok"):
            self.stdout.write(self.style.SUCCESS(f"✅ Webhook o'rnatildi: {webhook_url}"))
        else:
            self.stderr.write(f"❌ Xato: {resp.text}")
