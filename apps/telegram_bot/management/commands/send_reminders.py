"""
apps/telegram_bot/management/commands/send_reminders.py

Eslatmalar management command — cron orqali har kuni ishlatiladi.

Ishlatish:
    python manage.py send_reminders

Crontab:
    0 9 * * * cd /path/to/merged && python manage.py send_reminders
    0 18 * * * cd /path/to/merged && python manage.py send_reminders
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Yetkazish sanasi eslatmalarini yuborish"

    def handle(self, *args, **options):
        self.stdout.write("🔔 Eslatmalar tekshirilmoqda...")

        try:
            from apps.telegram_bot.bot import _handle_check_reminders
            _handle_check_reminders()
            self.stdout.write(self.style.SUCCESS("✅ Eslatmalar yuborildi!"))
        except Exception as e:
            self.stderr.write(f"❌ Xato: {e}")
            import traceback
            traceback.print_exc()