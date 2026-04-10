#!/bin/bash
# Statik fayllarni yig'ish va bazani yangilash
python manage.py collectstatic --no-input
python manage.py migrate

# Telegram botni fonda (background) ishga tushirish
python run_bot_polling.py &

# Web serverni (Django) ishga tushirish
gunicorn project.wsgi:application --bind 0.0.0.0:$PORT
