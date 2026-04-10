from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Ombor ogohlantirishini yuborish"
    def handle(self, *args, **options):
        from apps.telegram_bot.notify import notify_low_stock
        notify_low_stock()
        self.stdout.write(self.style.SUCCESS("✅ Ombor tekshirildi!"))
