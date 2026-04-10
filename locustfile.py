import os
import django
from locust import HttpUser, task, between, events

# Django sozlamalarini chaqirish (Token olish uchun)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings.base")
django.setup()

from rest_framework.authtoken.models import Token
from apps.users.models import User

# Barcha test foydalanuvchilar (botlar) uchun umumiy Token olamiz
admin_user = User.objects.filter(role__in=['admin', 'manager']).first()
if not admin_user:
    # Agar admin topilmasa, yaratamiz
    admin_user = User.objects.create_user(username='locust_tester', password='tastpass', role='admin')

auth_token, _ = Token.objects.get_or_create(user=admin_user)
GLOBAL_TOKEN = auth_token.key

class EMebelUser(HttpUser):
    # Har bir botning bosishlar (request) orasidagi tanaffusi: 1-3 soniya
    wait_time = between(1, 3)

    def on_start(self):
        """Har bir bot ishni boshlaganda token o'rnatiladi"""
        self.client.headers.update({"Authorization": f"Token {GLOBAL_TOKEN}"})

    @task(3) # Dashboard ko'p yuklanadi (3 karra ko'proq bosiladi)
    def load_dashboard(self):
        self.client.get("/api/dashboard/")

    @task(2) # Mahsulotlarni varaqlaydilar
    def load_products(self):
        self.client.get("/api/products/")

    @task(2) # Kategoriya varaqlari
    def load_categories(self):
        self.client.get("/api/categories/")

    @task(1) # Ba'zida buyurtmalar ro'yxatiga o'tadi
    def load_orders(self):
        self.client.get("/api/orders/")

    @task(1) # Bitta aniq buyurtmani ko'rib chiqish (masalan 1 yoki qandaydir topilgan)
    def get_finance_chart(self):
        self.client.get("/api/finance/chart/")

