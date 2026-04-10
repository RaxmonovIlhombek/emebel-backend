# settings/base.py

import os
from pathlib import Path
import environ

env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY    = env('SECRET_KEY', default='django-insecure-change-me')
DEBUG         = env.bool('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

DJANGO_APPS = [
    'daphne',
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = []

LOCAL_APPS = [
    'apps.users',
    'apps.products',
    'apps.orders',
    'apps.clients',
    'apps.warehouse',
    'apps.common',
    'apps.telegram_bot',
    'apps.payments',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'api',
    'drf_spectacular',
    'apps.notifications',
    'channels',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF      = 'project.urls'
WSGI_APPLICATION  = 'project.wsgi.application'
ASGI_APPLICATION  = 'project.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

AUTH_USER_MODEL   = 'users.User'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.template.context_processors.debug',
            'django.template.context_processors.request',
            'django.contrib.auth.context_processors.auth',
            'django.contrib.messages.context_processors.messages',
        ],
    },
}]

# ─── DATABASE ────────────────────────────────────────────────────────
# SQLite (development) — PostgreSQL ga o'tish uchun .env ga DATABASE_URL qo'shing
DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}
DATABASES['default']['CONN_MAX_AGE'] = 60

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
TIME_ZONE     = 'Asia/Tashkent'
USE_I18N      = True
USE_TZ        = True

CACHES = {
    'default': {
        'BACKEND':  'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'crm-cache',
        'TIMEOUT':  60,
    }
}

SESSION_ENGINE              = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE          = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

STATIC_URL   = '/static/'
STATIC_ROOT  = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STORAGES = {
    'default':    {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='')
GROQ_API_KEY       = env('GROQ_API_KEY', default='')
WEBAPP_URL         = env('WEBAPP_URL', default='')
SITE_URL           = env('SITE_URL',   default='http://localhost:8000')

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://e-mebel.uz",
    "https://www.e-mebel.uz",
]
CSRF_TRUSTED_ORIGINS = [
    "https://e-mebel.uz",
    "https://www.e-mebel.uz",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True

SPECTACULAR_SETTINGS = {
    'TITLE':   'e-Mebel CRM API',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# ─── JAZZMIN ─────────────────────────────────────────────────────────
JAZZMIN_SETTINGS = {
    "site_title":   "e-Mebel CRM",
    "site_header":  "e-Mebel",
    "site_brand":   "e-Mebel CRM",
    "site_logo":    "img/logo (2).png",
    "login_logo":   "img/logo (2).png",
    "site_icon":    "img/logo_icon.png",
    "welcome_sign": "🛋️ e-Mebel CRM ga xush kelibsiz!",
    "copyright":    "© 2026 e-Mebel CRM",
    "search_model": ["users.User", "clients.Client", "orders.Order"],
    "user_avatar":  None,
    "topmenu_links": [
        {"name": "🏠 Bosh sahifa",  "url": "admin:index",             "permissions": ["auth.view_user"]},
        {"name": "🖥️ CRM Tizim",   "url": "http://localhost:3000",   "new_window": True},
        {"name": "📄 API Docs",     "url": "/api/docs/",             "new_window": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    "order_with_respect_to": [
        "users",
        "clients",
        "orders",
        "products",
        "warehouse",
        "notifications",
        "telegram_bot",
    ],
    "icons": {
        # Auth
        "auth":                          "fas fa-lock",
        "auth.user":                     "fas fa-user",
        "auth.Group":                    "fas fa-users",
        # Users
        "users.user":                    "fas fa-user-tie",
        "users.message":                 "fas fa-envelope",
        # Clients
        "clients.client":                "fas fa-address-book",
        # Orders
        "orders.order":                  "fas fa-shopping-cart",
        "orders.payment":                "fas fa-money-bill-wave",
        "orders.contract":               "fas fa-file-contract",
        # Products
        "products.product":              "fas fa-couch",
        "products.category":             "fas fa-tags",
        # Warehouse
        "warehouse.stock":               "fas fa-warehouse",
        "warehouse.stockmovement":       "fas fa-exchange-alt",
        # Notifications
        "notifications.notification":    "fas fa-bell",
        # Telegram Bot
        "telegram_bot.botsession":       "fab fa-telegram",
        "telegram_bot.paymetransaction": "fas fa-credit-card",
        "telegram_bot.clicktransaction": "fas fa-credit-card",
        "telegram_bot.scheduledmessage": "fas fa-clock",
    },
    "default_icon_parents":  "fas fa-folder",
    "default_icon_children": "fas fa-circle",
    "related_modal_active":  True,
    "custom_css":  "admin/css/custom_open.css",
    "custom_js":   None,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "users.user":      "collapsible",
        "orders.order":    "horizontal_tabs",
        "products.product": "horizontal_tabs",
    },
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text":      False,
    "footer_small_text":      False,
    "body_small_text":        False,
    "brand_small_text":       False,
    "brand_colour":           "navbar-white navbar-light",
    "accent":                 "accent-primary",
    "navbar":                 "navbar-white navbar-light",
    "no_navbar_border":       False,
    "navbar_fixed":           True,
    "layout_fixed":           True,
    "footer_fixed":           False,
    "sidebar_fixed":          True,
    "sidebar":                "sidebar-light-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style":   False,
    "theme":                  "flatly",
    "dark_mode_theme":        None,
    "button_classes": {
        "primary":   "btn-primary",
        "secondary": "btn-secondary",
        "info":      "btn-info",
        "warning":   "btn-warning",
        "danger":    "btn-danger",
        "success":   "btn-success",
    },
    "actions_sticky_top":     True,
}

# ─── PAYME / CLICK (ixtiyoriy) ────────────────────────────────────────
PAYME_MERCHANT_ID = env('PAYME_MERCHANT_ID', default='')
PAYME_KEY         = env('PAYME_KEY',         default='')
PAYME_TEST_MODE   = env.bool('PAYME_TEST_MODE', default=True)
CLICK_MERCHANT_ID = env('CLICK_MERCHANT_ID', default='')
CLICK_SERVICE_ID  = env('CLICK_SERVICE_ID',  default='')
