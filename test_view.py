import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from apps.users.models import User
from apps.orders.models import Order
from apps.clients.models import Client
from rest_framework.test import APIRequestFactory
from api.views import OrderDetailView
from django.contrib.auth import authenticate

users = User.objects.filter(role='client')
if not users.exists():
    print("No client users found")
else:
    for u in users:
        print(f"User: {u.username}, role: {u.role}, hasattr client_profile: {hasattr(u, 'client_profile')}, client_profile={getattr(u, 'client_profile', None)}")
        
    client_user = users.first()
    client_profile = getattr(client_user, 'client_profile', None)
    if client_profile:
        orders = Order.objects.filter(client=client_profile)
        if orders.exists():
            order = orders.first()
            factory = APIRequestFactory()
            view = OrderDetailView.as_view()
            request = factory.get(f'/api/orders/{order.id}/')
            from rest_framework.request import Request
            from rest_framework.parsers import JSONParser
            request.user = client_user
            
            try:
                response = view(request, pk=order.id)
                print("Endpoint response status:", response.status_code)
                print("Endpoint response data:", response.data if hasattr(response, 'data') else response.content)
            except Exception as e:
                print("Endpoint raised exception:", type(e), e)
        else:
            print("Client has no orders")
    else:
        print("Client user has no client profile")
