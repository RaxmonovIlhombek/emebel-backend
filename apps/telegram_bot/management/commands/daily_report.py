from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Kunlik hisobotni Telegram ga yuborish"
    def handle(self, *args, **options):
        from apps.telegram_bot.notify import send_daily_report
        send_daily_report()
        self.stdout.write(self.style.SUCCESS("✅ Kunlik hisobot yuborildi!"))
