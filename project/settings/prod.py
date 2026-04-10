from .base import *
import os

DEBUG = False

# Production host larni .env dan oling (masalan: e-mebel.render.com)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

# Xavfsizlik sozlamalari
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=True)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=True)

# Static files
STATIC_ROOT = BASE_DIR / 'staticfiles'
