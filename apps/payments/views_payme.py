import time
from base64 import b64decode
from decimal import Decimal
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.orders.models import Order, Payment
from .models import Transaction

class PaymeCallbackView(APIView):
    """
    Payme JSON-RPC 2.0 callback.
    Hujjat: https://developer.help.paycom.uz/ru/methods-and-responses
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. Basic Auth tekshirish (Payme xavfsizligi)
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            return self.error(-32504, "Invalid Authorization header")
            
        encoded_key = auth_header.split(' ')[1]
        decoded_key = b64decode(encoded_key).decode()
        merchant_key = getattr(settings, 'PAYME_KEY', 'secret')
        
        # Payme key: "Paycom:{secret_key}" formatida keladi
        if f'Paycom:{merchant_key}' != decoded_key:
            return self.error(-32504, "Invalid credentials")

        data   = request.data
        method = data.get('method')
        params = data.get('params', {})
        rpc_id = data.get('id')

        # 2. Metodlarni dispatch qilish
        if method == 'CheckPerformTransaction':
            return self.check_perform_transaction(params, rpc_id)
        elif method == 'CreateTransaction':
            return self.create_transaction(params, rpc_id)
        elif method == 'PerformTransaction':
            return self.perform_transaction(params, rpc_id)
        elif method == 'CheckTransaction':
            return self.check_transaction(params, rpc_id)
        elif method == 'CancelTransaction':
            return self.cancel_transaction(params, rpc_id)

        return self.error(-32601, "Method not found")

    def check_perform_transaction(self, params, rpc_id):
        order_id = params.get('account', {}).get('order_id')
        amount   = params.get('amount')
        
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return self.error(-31050, "Order not found", rpc_id, "order_id")

        # Summa tiyinlarda (so'm * 100)
        expected_amount = int(order.remaining_amount * 100)
        if int(amount) != expected_amount:
            return self.error(-31001, f"Invalid amount. Expected {expected_amount}", rpc_id, "amount")

        return Response({
            "result": {"allow": True},
            "id": rpc_id
        })

    def create_transaction(self, params, rpc_id):
        id_trans = params.get('id') # Payme transaksiyasi ID si
        time_ms  = params.get('time')
        amount   = params.get('amount')
        order_id = params.get('account', {}).get('order_id')

        # Avval bu ID dagi tranzaksiyani tekshiramiz
        trans = Transaction.objects.filter(provider='payme', provider_id=id_trans).first()
        if trans:
            if trans.status != 'pending':
                return self.error(-31008, "Transaction state invalid", rpc_id)
            return Response({
                "result": {
                    "create_time": int(trans.created_at.timestamp() * 1000),
                    "transaction": str(trans.id),
                    "state": 1
                },
                "id": rpc_id
            })

        # Order to'langanmi?
        order = Order.objects.get(id=order_id)
        if order.payment_status == 'paid':
            return self.error(-31007, "Order already paid", rpc_id)

        # Yangi tranzaksiya
        Transaction.objects.create(
            provider='payme', provider_id=id_trans,
            order=order, amount=Decimal(amount)/100, 
            status='pending', request_data=params
        )

        return Response({
            "result": {
                "create_time": int(time.time() * 1000),
                "transaction": id_trans,
                "state": 1
            },
            "id": rpc_id
        })

    def perform_transaction(self, params, rpc_id):
        id_trans = params.get('id')
        trans = Transaction.objects.filter(provider='payme', provider_id=id_trans).first()
        
        if not trans:
            return self.error(-31003, "Transaction not found", rpc_id)

        if trans.status == 'success':
            return Response({
                "result": {
                    "transaction": id_trans,
                    "perform_time": int(time.time() * 1000), # Bu yerda real perform_time kerak
                    "state": 2
                },
                "id": rpc_id
            })

        # To'lovni yakunlash
        trans.status = 'success'
        trans.save()
        
        # Payment yaratish
        Payment.objects.create(
            order=trans.order, amount=trans.amount,
            method='payme', external_id=id_trans,
            is_confirmed=True, note="Payme thru callback"
        )
        
        # Order holatini yangilash
        order = trans.order
        order.paid_amount += trans.amount
        if order.paid_amount >= order.total_amount:
            order.payment_status = 'paid'
        order.save()

        # Telegram xabarnoma
        from apps.telegram_bot.notify import notify_payment_received
        notify_payment_received(order, trans.amount, 'Payme')

        return Response({
            "result": {
                "transaction": id_trans,
                "perform_time": int(time.time() * 1000),
                "state": 2
            },
            "id": rpc_id
        })

    def check_transaction(self, params, rpc_id):
        id_trans = params.get('id')
        trans = Transaction.objects.filter(provider='payme', provider_id=id_trans).first()
        if not trans:
            return self.error(-31003, "Transaction not found", rpc_id)
        
        state = 1 if trans.status == 'pending' else (2 if trans.status == 'success' else -1)
        return Response({
            "result": {
                "create_time": int(trans.created_at.timestamp() * 1000),
                "perform_time": 0, # Muvaffaqiyatli bo'lsa Perform time
                "cancel_time": 0,
                "transaction": id_trans,
                "state": state,
                "reason": None
            },
            "id": rpc_id
        })

    def cancel_transaction(self, params, rpc_id):
        id_trans = params.get('id')
        reason   = params.get('reason')
        trans = Transaction.objects.filter(provider='payme', provider_id=id_trans).first()
        if not trans:
            return self.error(-31003, "Transaction not found", rpc_id)
        
        trans.status = 'failed'
        trans.error_message = f"Payme Reason: {reason}"
        trans.save()
        
        return Response({
            "result": {
                "transaction": id_trans,
                "cancel_time": int(time.time() * 1000),
                "state": -1
            },
            "id": rpc_id
        })

    def error(self, code, message, rpc_id=None, data_field=None):
        error_obj = {"code": code, "message": {"ru": message, "uz": message, "en": message}}
        if data_field:
            error_obj["data"] = data_field
        return Response({
            "error": error_obj,
            "id": rpc_id,
            "result": None
        })
