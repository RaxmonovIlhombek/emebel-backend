import hashlib
from decimal import Decimal
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from apps.orders.models import Order, Payment
from .models import Transaction

class ClickCallbackView(APIView):
    """
    Click to'lov tizimi uchun callback.
    Hujjat: https://docs.click.uz/click-checkout-merchant/
    """
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        click_trans_id    = data.get('click_trans_id')
        service_id        = data.get('service_id')
        click_paydoc_id   = data.get('click_paydoc_id')
        merchant_trans_id = data.get('merchant_trans_id') # Bizning order_id
        amount            = data.get('amount')
        action            = data.get('action')
        error             = data.get('error')
        error_note        = data.get('error_note')
        sign_time         = data.get('sign_time')
        sign_string       = data.get('sign_string')

        # 1. Signature tekshirish
        secret_key = getattr(settings, 'CLICK_KEY', 'secret') # .env da CLICK_KEY bo'lishi kerak
        # sign_string = md5(click_trans_id + service_id + secret_key + merchant_trans_id + (merchant_prepare_id если есть) + amount + action + sign_time)
        # Merchant_prepare_id action=1 da keladi, action=0 da yo'q.
        
        # Soddalashtirilgan MD5 tekshiruvi (Hujjatga ko'ra)
        prepare_id = data.get('merchant_prepare_id', '')
        my_sign = hashlib.md5(
            f"{click_trans_id}{service_id}{secret_key}{merchant_trans_id}{prepare_id}{amount}{action}{sign_time}".encode()
        ).hexdigest()

        if my_sign != sign_string:
            return Response({"error": "-1", "error_note": "SIGN_CHECK_FAILED"}, status=200)

        # 2. Buyurtmani topish
        try:
            order = Order.objects.get(id=merchant_trans_id)
        except Order.DoesNotExist:
            return Response({"error": "-5", "error_note": "ORDER_NOT_FOUND"}, status=200)

        # 3. Action = 0 (PREPARE)
        if str(action) == '0':
            # Summani tekshirish
            if Decimal(amount) < order.remaining_amount * Decimal('0.9'): # Kamida 90% to'lanishi kerak (misol)
                return Response({"error": "-2", "error_note": "INVALID_AMOUNT"}, status=200)

            # Tranzaksiyani yaratish yoki yangilash
            Transaction.objects.update_or_create(
                provider='click', provider_id=click_trans_id,
                defaults={'order': order, 'amount': amount, 'status': 'pending', 'request_data': data}
            )
            
            return Response({
                "click_trans_id":      click_trans_id,
                "merchant_trans_id":   merchant_trans_id,
                "merchant_prepare_id": merchant_trans_id, # Prepare_id sifatida order_id ni qaytaramiz
                "error":               "0",
                "error_note":          "Success"
            })

        # 4. Action = 1 (COMPLETE)
        if str(action) == '1':
            trans = Transaction.objects.filter(provider='click', provider_id=click_trans_id).first()
            if not trans:
                return Response({"error": "-6", "error_note": "TRANSACTION_NOT_FOUND"}, status=200)

            if str(error) != '0':
                trans.status = 'failed'
                trans.error_message = error_note
                trans.save()
                return Response({"error": error, "error_note": error_note})

            # To'lov muvaffaqiyatli!
            trans.status = 'success'
            trans.response_data = data
            trans.save()

            # Payment modeliga yozish
            Payment.objects.create(
                order        = order,
                amount       = amount,
                method       = 'click',
                external_id  = click_trans_id,
                is_confirmed = True,
                note         = f"Click thru {click_paydoc_id}"
            )
            
            # Order to'lov holatini yangilash model save() metodida avtomatlashtirilgan (taxminan)
            # Lekin bu yerda qo'lda ham tekshirish mumkin
            order.paid_amount += Decimal(amount)
            if order.paid_amount >= order.total_amount:
                order.payment_status = 'paid'
            elif order.paid_amount > 0:
                order.payment_status = 'partial'
            order.save()

            # Telegram xabarnoma (Ixtiyoriy)
            from apps.telegram_bot.notify import notify_payment_received
            notify_payment_received(order, amount, 'Click')

            return Response({
                "click_trans_id":    click_trans_id,
                "merchant_trans_id": merchant_trans_id,
                "error":             "0",
                "error_note":        "Success"
            })

        return Response({"error": "-3", "error_note": "ACTION_NOT_FOUND"}, status=200)
