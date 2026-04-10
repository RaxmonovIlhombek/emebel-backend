import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from apps.users.models import User
from rest_framework.authtoken.models import Token

BASE_URL = 'http://127.0.0.1:8000/api'

def get_token(role):
    # Find active user by role
    user = User.objects.filter(role=role, is_active=True).first()
    if not user:
        return None
    token, _ = Token.objects.get_or_create(user=user)
    return token.key, user

roles_to_test = ['admin', 'manager', 'accountant', 'worker', 'client']

endpoints = {
    'Dashboard (IsStaff)': ('GET', '/dashboard/'),
    'Finance Summary (IsFinance)': ('GET', '/finance/summary/'),
    'AI Assistant (IsStaff)': ('POST', '/ai/'),
    'Clients List (IsStaff)': ('GET', '/clients/'),
    'Categories (IsStaff)': ('GET', '/categories/'),
    'Orders (IsAuth)': ('GET', '/orders/'),
}

results = {}

for role in roles_to_test:
    res = get_token(role)
    if not res:
        print(f"[{role.upper()}] No active user found.")
        continue
    token, user = res
    print(f"\n--- Testing role: {role.upper()} (User: {user.username}) ---")
    headers = {'Authorization': f'Token {token}'}
    
    role_results = {}
    for name, (method, path) in endpoints.items():
        url = BASE_URL + path
        if method == 'GET':
            r = requests.get(url, headers=headers)
        elif method == 'POST':
            r = requests.post(url, headers=headers, json={"message": "hello"})
        
        status = r.status_code
        print(f"{name:30}: HTTP {status}")
        role_results[name] = status
    
    results[role] = role_results

print("\n=== SUMMARY ===")
print("If Client gets 403 on Staff/Finance APIs, the RBAC is WORKING.")
for role, vals in results.items():
    print(f"Role: {role}")
    for name, code in vals.items():
        print(f"  {code} - {name}")

