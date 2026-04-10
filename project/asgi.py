import os
import django
from django.core.asgi import get_asgi_application

# 1. AVVAL: Sozlamalar faylini ko'rsatamiz
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings.base')

# 2. KEYIN: Djangoni tayyorlaymiz (bu juda muhim!)
django.setup()

# 3. UNDAN KEYIN: ASGI ilovasini olamiz
django_asgi_app = get_asgi_application()

# 4. OXIRIDA: Modelga yoki sozlamalarga bog'liq narsalarni import qilamiz
# Faqat django.setup() dan keyin bu importlar xato bermaydi
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.notifications.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})