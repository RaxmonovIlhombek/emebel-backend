from django.db.models import Sum
from apps.orders.models import Order
from apps.products.models import Product
from apps.clients.models import Client

def get_dashboard_stats():
    stats = {
        'total_orders': Order.objects.count(),
        'new_orders': Order.objects.filter(status='new').count(),
        'in_production': Order.objects.filter(status='production').count(),
        'total_clients': Client.objects.count(),
        'active_products': Product.objects.filter(is_active=True).count(),
        'total_revenue': Order.objects.filter(status='delivered').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
    }
    return stats