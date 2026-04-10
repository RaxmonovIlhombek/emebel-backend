import os, django
from django.conf import settings
from django.db.models import Min, Max
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()
from apps.orders.models import Order
res = Order.objects.aggregate(Min('created_at'), Max('created_at'), count=django.db.models.Count('id'))
print(res)
