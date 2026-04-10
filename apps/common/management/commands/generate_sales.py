import random
import uuid
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction, models  # 'models' va 'transaction' qo'shildi
from django.apps import apps


class Command(BaseCommand):
    help = "CRM uchun 1 yillik realistik va kompleks savdo tarixini yaratish"

    def add_arguments(self, parser):
        # Terminaldan kiruvchi buyruqlar uchun parametrlar
        parser.add_argument('--orders', type=int, default=1000, help="Buyurtmalar soni")
        parser.add_argument('--clients', type=int, default=100, help="Mijozlar soni")
        parser.add_argument('--clear', action='store_true', help="Eski ma'lumotlarni o'chirish")

    def handle(self, *args, **options):
        order_count = options['orders']
        client_count = options['clients']  # Terminaldan kelgan son

        if options['clear']:
            self.clear_data()

        self.stdout.write(f"🚀 Generatsiya boshlandi: {order_count} ta buyurtma va {client_count} ta mijoz...")

        # 1. Tayyorgarlik (Asosiy obyektlarni yaratish)
        manager = self.get_or_create_admin()
        categories = self.setup_categories()
        products = self.setup_products(categories, manager)

        # Mijozlar sonini funksiyaga uzatamiz
        clients = self.setup_clients(client_count)

        # 2. Savdo Simulyatsiyasi (Bitta tranzaksiya ichida)
        with transaction.atomic():
            self.create_realistic_sales(order_count, clients, products, manager)

        self.stdout.write(self.style.SUCCESS(f"\n✅ Muvaffaqiyatli yakunlandi!"))

    def get_or_create_admin(self):
        from apps.users.models import User
        user, _ = User.objects.get_or_create(
            username='admin_ali',
            defaults={'role': 'admin', 'first_name': 'Ali', 'is_staff': True}
        )
        if _:
            user.set_password('password123')
            user.save()
        return user

    def setup_categories(self):
        from apps.products.models import Category
        names = ['Yotoqxona', 'Oshxona', 'Mehmonxona', 'Ofis', 'Yumshoq mebel', 'Bolalar uchun']
        return [Category.objects.get_or_create(name=n)[0] for n in names]

    def setup_products(self, categories, user):
        from apps.products.models import Product
        from apps.warehouse.models import StockMovement, Stock

        products = []
        types = ['Divan', 'Shkaf', 'Stol', 'Kreslo', 'Krovat', 'Tumba', 'Oshxona garnituri']

        for _ in range(40):
            cost = random.randint(1200000, 8000000)
            p = Product.objects.create(
                category=random.choice(categories),
                name=f"{random.choice(types)} {uuid.uuid4().hex[:4].upper()}",
                sku=f"MEB-{random.randint(10000, 99999)}",
                cost_price=cost,
                selling_price=cost + random.randint(400000, 3000000),
                is_active=True
            )
            # Dastlabki stok (har bir mahsulotdan 1000 tadan)
            Stock.objects.get_or_create(product=p, defaults={'quantity': 1000})
            StockMovement.objects.create(
                product=p, movement_type='in', quantity=1000,
                reason="Boshlang'ich qoldiq", performed_by=user
            )
            products.append(p)
        return products

    def setup_clients(self, count):
        from apps.clients.models import Client

        first_names = ['Azizbek', 'Otabek', 'Sardor', 'Dilshod', 'Javohir', 'Madina', 'Nigora', 'Zuhra', 'Rustam',
                       'Faxriddin']
        last_names = ['Rahimov', 'Ganiyev', 'Abdullayev', 'Karimov', 'Usmonov', 'Toirov', 'Soliqov', 'Azimov']
        regions = ['Toshkent', 'Samarqand', 'Farg\'ona', 'Andijon', 'Namangan', 'Buxoro', 'Qashqadaryo', 'Xorazm']

        clients = []
        self.stdout.write(f"👥 {count} ta mijoz shakllantirilmoqda...")

        for i in range(count):
            full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
            phone = f"+998{random.choice(['90', '91', '93', '94', '95', '97', '99'])}{random.randint(100, 999)}{random.randint(10, 99)}{random.randint(10, 99)}"

            c = Client.objects.create(
                name=full_name,
                phone=phone,
                region=random.choice(regions),
                district="Markaziy tuman",
                address=f"Mustaqillik ko'chasi, {random.randint(1, 100)}-uy"
            )
            clients.append(c)
        return clients

    def create_realistic_sales(self, total_orders, clients, products, manager):
        from apps.orders.models import Order, OrderItem, Payment
        from apps.warehouse.models import StockMovement, Stock

        start_date = timezone.now() - timedelta(days=365)

        for i in range(total_orders):
            # --- REALISTIK SANA GENERATSIYASI ---
            month_weights = [0.5, 0.4, 0.9, 0.6, 0.5, 0.4, 0.3, 0.5, 1.2, 0.8, 0.7, 1.5]
            chosen_month = random.choices(range(1, 13), weights=month_weights)[0]

            day = random.randint(1, 28)
            hour = random.choices(range(24),
                                  weights=[1, 1, 1, 1, 1, 1, 2, 5, 10, 12, 15, 14, 12, 15, 18, 20, 18, 15, 10, 5, 3, 2,
                                           1, 1])[0]

            # 2024 va 2025 o'rtasida sana yaratish
            target_date = timezone.datetime(2025 if chosen_month < 4 else 2024, chosen_month, day, hour,
                                            random.randint(0, 59), tzinfo=timezone.get_current_timezone())

            # --- BUYURTMA ---
            order = Order.objects.create(
                order_number=f"ORD-{target_date.strftime('%y%m%d')}-{uuid.uuid4().hex[:4].upper()}",
                client=random.choice(clients),
                manager=manager,
                status='completed' if target_date < timezone.now() - timedelta(days=5) else 'new'
            )
            # Created_at auto_now_add bo'lgani uchun filter+update bilan o'zgartiramiz
            Order.objects.filter(id=order.id).update(created_at=target_date)

            # --- SAVATCHA ---
            current_total = Decimal('0')
            items_count = random.choices([1, 2, 3, 4], weights=[60, 25, 10, 5])[0]

            for _ in range(items_count):
                p = random.choice(products)
                qty = random.randint(1, 2)
                price = p.selling_price

                OrderItem.objects.create(order=order, product=p, quantity=qty, price=price)

                # Ombor harakati
                StockMovement.objects.create(
                    product=p, movement_type='out', quantity=qty,
                    reason=f"Sotuv {order.order_number}", performed_by=manager,
                    created_at=target_date
                )
                # Ombor qoldig'ini kamaytirish (models.F bilan xavfsiz yangilash)
                Stock.objects.filter(product=p).update(quantity=models.F('quantity') - qty)

                current_total += (price * qty)

            # --- TO'LOV ---
            method = random.choice(['cash', 'card', 'transfer'])
            pay_prob = random.random()

            if pay_prob < 0.9:  # 90% holatda to'liq to'langan
                paid = current_total
                status = 'paid'
                Payment.objects.create(
                    order=order, amount=paid, method=method,
                    is_confirmed=True, created_at=target_date + timedelta(minutes=20)
                )
            elif pay_prob < 0.97:  # 7% holatda qisman to'langan
                paid = current_total / 2
                status = 'partial'
                Payment.objects.create(order=order, amount=paid, method=method, created_at=target_date)
            else:  # 3% to'lanmagan
                paid = 0
                status = 'unpaid'

            Order.objects.filter(id=order.id).update(
                total_amount=current_total,
                paid_amount=paid,
                payment_status=status
            )

            if i % 100 == 0:
                self.stdout.write(f"⏳ {i} ta buyurtma yaratildi...")

    def clear_data(self):
        from apps.orders.models import Order, OrderItem, Payment
        from apps.products.models import Product, Category
        from apps.clients.models import Client
        from apps.warehouse.models import Stock, StockMovement

        # Agarda Payme va Click app'lari bo'lsa, ularni ham import qilamiz
        try:
            from apps.payments.models import PaymeTransaction, \
                ClickTransaction  # App nomi sizda boshqacha bo'lishi mumkin
        except ImportError:
            PaymeTransaction, ClickTransaction = None, None

        self.stdout.write("🗑️ Bazani tozalash boshlandi (Himoyalangan ma'lumotlar bilan)...")

        # 1. Birinchi navbatda barcha bog'liq tranzaksiyalarni o'chiramiz
        if PaymeTransaction:
            PaymeTransaction.objects.all().delete()
        if ClickTransaction:
            ClickTransaction.objects.all().delete()

        # 2. Keyin qolgan modellarni ketma-ketlikda o'chiramiz
        Payment.objects.all().delete()
        OrderItem.objects.all().delete()

        # Endi Order'ni o'chirishda ProtectedError chiqmaydi
        Order.objects.all().delete()

        StockMovement.objects.all().delete()
        Stock.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Client.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("✅ Baza tozalandi!"))
        Payment.objects.all().delete()
        OrderItem.objects.all().delete()
        Order.objects.all().delete()
        StockMovement.objects.all().delete()
        Stock.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Client.objects.all().delete()