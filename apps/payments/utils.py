import base64
from django.conf import settings
from decimal import Decimal

def generate_payme_link(order_id, amount):
    """
    Payme to'lov linkini generatsiya qilish.
    Protokol: https://help.paycom.uz/ru/methods-and-responses/generate-checkout-url
    """
    merchant_id = getattr(settings, 'PAYME_MERCHANT_ID', '')
    # Summa tiyinlarda bo'lishi kerak (so'm * 100)
    amount_tiyin = int(Decimal(amount) * 100)
    
    # params: m={merchant_id};ac.order_id={order_id};a={amount}
    params = f"m={merchant_id};ac.order_id={order_id};a={amount_tiyin}"
    encode_params = base64.b64encode(params.encode()).decode()
    
    base_url = "https://checkout.paycom.uz" # Test rejimida ham shunday bo'lishi mumkin
    return f"{base_url}/{encode_params}"

def generate_click_link(order_id, amount):
    """
    Click to'lov linkini generatsiya qilish.
    Protokol: https://docs.click.uz/click-checkout/
    """
    merchant_id = getattr(settings, 'CLICK_MERCHANT_ID', '')
    service_id  = getattr(settings, 'CLICK_SERVICE_ID', '')
    
    # URL: https://my.click.uz/services/pay?service_id={service_id}&merchant_id={merchant_id}&amount={amount}&transaction_param={order_id}
    base_url = "https://my.click.uz/services/pay"
    return f"{base_url}?service_id={service_id}&merchant_id={merchant_id}&amount={amount}&transaction_param={order_id}"
