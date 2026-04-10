"""
project/celery.py — Celery konfiguratsiya

Ishga tushirish:
  celery -A project worker -l info
  celery -A project beat   -l info
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.base')

app = Celery('emebel_crm')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.timezone = 'Asia/Tashkent'

app.conf.beat_schedule = {
    'send-scheduled-messages': {
        'task':     'apps.telegram_bot.tasks.send_scheduled_messages',
        'schedule': 60.0,
    },
    'daily-debt-reminders': {
        'task':     'apps.telegram_bot.tasks.send_debt_reminders',
        'schedule': crontab(hour=9, minute=0),
    },
    'daily-delivery-reminders': {
        'task':     'apps.telegram_bot.tasks.send_delivery_reminders',
        'schedule': crontab(hour=18, minute=0),
    },
    'daily-low-stock-check': {
        'task':     'apps.telegram_bot.tasks.check_low_stock',
        'schedule': crontab(hour=8, minute=0),
    },
    'daily-report': {
        'task':     'apps.telegram_bot.tasks.send_daily_report_task',
        'schedule': crontab(hour=20, minute=0),
    },
    'check-payme-payments': {
        'task':     'apps.telegram_bot.tasks.check_payme_payments',
        'schedule': 300.0,
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


def schedules():
    return None