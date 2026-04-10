import os
import random
import django
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone

# +++ Setup Django +++
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from apps.products.models import Category, Product
from apps.clients.models import Client
from apps.orders.models import Order, OrderItem, Payment, Expense
from apps.users.models import User
from apps.warehouse.models import Stock

def clear_db():
    print("Baza tozalanmoqda...")
    Order.objects.all().delete()
    Client.objects.all().delete()
    Product.objects.all().delete()
    Category.objects.all().delete()
    Expense.objects.all().delete()
    print("Ma'lumotlar o'chirildi.")

def seed_data():
    # 1. Kategoriyalar
    cats = {
        'oshxona': Category.objects.get_or_create(name="Loft Oshxona")[0],
        'living':  Category.objects.get_or_create(name="Loft Mehmonxona")[0],
        'bedroom': Category.objects.get_or_create(name="Loft Yotoqxona")[0],
        'office':  Category.objects.get_or_create(name="Loft Ofis")[0],
    }

    # 2. Mahsulotlar (5 ta rasmimiz bor)
    # Rasm nomlari (media/products/ papkasida bo'lishi kerak):
    # loft_kitchen.jpg, loft_living.jpg, loft_bed.jpg, loft_wardrobe.jpg, loft_table.jpg

    products_data = [
        {'cat': 'oshxona', 'name': 'Industrial Loft Oshxona', 'sku': 'K-LOFT-01', 'price': 35_000_000, 'cost': 22_000_000, 'img': 'products/loft_kitchen.jpg'},
        {'cat': 'oshxona', 'name': 'Minimalist Loft Oshxona', 'sku': 'K-LOFT-02', 'price': 28_000_000, 'cost': 18_000_000, 'img': 'products/loft_kitchen.jpg'},
        {'cat': 'living',  'name': 'Chester Loft Divan',      'sku': 'L-SOFA-01', 'price': 12_500_000, 'cost': 7_200_000,  'img': 'products/loft_living.jpg'},
        {'cat': 'living',  'name': 'Loft Jurnal Stoli',      'sku': 'L-TABL-01', 'price': 3_200_000,  'cost': 1_100_000,  'img': 'products/loft_table.jpg'},
        {'cat': 'bedroom', 'name': 'Loft Temir Karovat',     'sku': 'B-BED-01',  'price': 8_900_000,  'cost': 5_400_000,  'img': 'products/loft_bed.jpg'},
        {'cat': 'bedroom', 'name': 'Loft Shkaf-Garderob',    'sku': 'B-WARD-01', 'price': 15_600_000, 'cost': 9_800_000,  'img': 'products/loft_wardrobe.jpg'},
        {'cat': 'office',  'name': 'Masiv Ofis Stoli',       'sku': 'O-DESK-01', 'price': 6_800_000,  'cost': 3_200_000,  'img': 'products/loft_table.jpg'},
        {'cat': 'office',  'name': 'Ergonomik Loft Kreslo',  'sku': 'O-CHAIR-01', 'price': 4_500_000,  'cost': 2_100_000,  'img': 'products/loft_living.jpg'},
    ]

    all_prods = []
    for p in products_data:
        prod = Product.objects.create(
            category=cats[p['cat']],
            name=p['name'],
            sku=p['sku'],
            selling_price=p['price'],
            cost_price=p['cost'],
            image=p['img'],
            material="Metall, Yog'och, Charm",
            is_active=True
        )
        Stock.objects.update_or_create(product=prod, defaults={'quantity': random.randint(5, 50)})
        all_prods.append(prod)

    # 3. Mijozlar
    clients = []
    client_names = [
        "Jasur Ahrorov", "Malika Saidova", "Sherzod Karimov", "Dilorom Usmonova", 
        "Alisher Tursunov", "Zilola Boboyeva", "Mansur Nabiyev", "Nodira Rahimova", 
        "Rustam Vahobov", "Feruza Shokirova", "Akmal Olimov", "Gulzoda Islomova",
        "Botir Yusupov", "Kamola Aminova", "Sanjar Ergashev"
    ]
    for name in client_names:
        c = Client.objects.create(
            name=name,
            phone=f"+998(90) {random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}",
            region="Toshkent",
            address="Yashnobod tumani, Loft ko'chasi"
        )
        clients.append(c)

    # 4. 200 ta Buyurtmalar (so'nggi 90 kun)
    print("200 ta buyurtma simulyatsiyasi boshlandi...")
    now = timezone.now()
    admin_user = User.objects.filter(is_superuser=True).first()
    
    statuses = ['new', 'pending', 'production', 'ready', 'delivered', 'completed']
    p_methods = ['cash', 'card', 'transfer']

    for i in range(200):
        # Sana: Bugun dan 90 kun oldingacha
        days_ago = random.randint(0, 90)
        c_at = now - timedelta(days=days_ago)
        
        # Tasodifiy mijoz
        cl = random.choice(clients)
        
        order = Order.objects.create(
            client=cl,
            manager=admin_user,
            status=random.choice(statuses),
            created_at=c_at,
            order_number=f"MB{c_at.strftime('%Y%m%d')}{i:04d}"
        )

        # 1-3 ta mahsulot har bir buyurtmada
        items_count = random.randint(1, 3)
        total_sum = 0
        for _ in range(items_count):
            p = random.choice(all_prods)
            qty = random.randint(1, 2)
            OrderItem.objects.create(
                order=order,
                product=p,
                quantity=qty,
                price=p.selling_price
            )
            total_sum += (p.selling_price * qty)
        
        order.total_amount = total_sum
        
        # To'lov simulyatsiyasi
        # Agar buyurtma 'completed' yoki 'delivered' bo'lsa - to'liq to'langan
        if order.status in ['completed', 'delivered']:
            order.paid_amount = total_sum
            order.payment_status = 'paid'
            pay = Payment.objects.create(
                order=order,
                amount=total_sum,
                method=random.choice(p_methods),
                is_confirmed=True
            )
            # Override auto_now_add
            Payment.objects.filter(pk=pay.pk).update(created_at=c_at + timedelta(hours=random.randint(1,48)))
            
        elif random.random() > 0.5: # 50% ehtimol bilan qisman to'lov
            paid = total_sum * Decimal(str(random.uniform(0.3, 0.7)))
            order.paid_amount = paid
            order.payment_status = 'partial'
            pay = Payment.objects.create(
                order=order,
                amount=paid,
                method=random.choice(p_methods),
                is_confirmed=True
            )
            # Override auto_now_add
            Payment.objects.filter(pk=pay.pk).update(created_at=c_at + timedelta(hours=random.randint(1,12)))
        
        order.save()
        # created_at ni save() dan keyin qayta yozamiz
        Order.objects.filter(pk=order.pk).update(created_at=c_at)

    # 5. Xarajatlar (Oyliklar, Ijara)
    for m in range(3):
        e_date = now - timedelta(days=m*30)
        ex1 = Expense.objects.create(category='rent', amount=15_000_000, date=e_date, note="Showroom ijara")
        Expense.objects.filter(pk=ex1.pk).update(created_at=e_date)
        
        ex2 = Expense.objects.create(category='salary', amount=25_000_000, date=e_date, note="Jamoa oyliklari")
        Expense.objects.filter(pk=ex2.pk).update(created_at=e_date)
        
        ex3 = Expense.objects.create(category='materials', amount=120_000_000, date=e_date, note="Materiallar")
        Expense.objects.filter(pk=ex3.pk).update(created_at=e_date)

    print(f"Tayyor! 200 ta buyurtma va {len(all_prods)} xil mahsulot qo'shildi.")

if __name__ == "__main__":
    clear_db()
    seed_data()
