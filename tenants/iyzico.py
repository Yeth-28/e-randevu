"""
iyzico Ödeme Entegrasyonu
Sandbox: https://sandbox-api.iyzipay.com
"""
import hashlib
import hmac
import base64
import json
import uuid
import requests
from django.conf import settings


PLANS = {
    'free':       {'name': 'Ücretsiz Plan', 'monthly_price': 0,   'yearly_total': 0},
    'pro':        {'name': 'Pro Plan',      'monthly_price': 499,  'yearly_total': 4990},
    'enterprise': {'name': 'Kurumsal Plan', 'monthly_price': 999,  'yearly_total': 9990},
}


def get_iyzico_config():
    return {
        'api_key':    getattr(settings, 'IYZICO_API_KEY',    'sandbox-api-key'),
        'secret_key': getattr(settings, 'IYZICO_SECRET_KEY', 'sandbox-secret-key'),
        'base_url':   getattr(settings, 'IYZICO_BASE_URL',   'https://sandbox-api.iyzipay.com'),
    }


def _generate_auth_header(api_key, secret_key, random_str, body_str):
    hash_str = api_key + random_str + secret_key + body_str
    digest   = hmac.new(secret_key.encode('utf-8'), hash_str.encode('utf-8'), hashlib.sha256).digest()
    b64      = base64.b64encode(digest).decode('utf-8')
    return f"IYZWS {api_key}:{b64}"


def _make_request(endpoint, payload):
    cfg        = get_iyzico_config()
    random_str = str(uuid.uuid4())
    body_str   = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    auth       = _generate_auth_header(cfg['api_key'], cfg['secret_key'], random_str, body_str)
    headers    = {
        'Content-Type': 'application/json; charset=utf-8',
        'Accept':       'application/json',
        'x-iyzi-rnd':   random_str,
        'Authorization': auth,
    }
    try:
        resp = requests.post(cfg['base_url'] + endpoint, headers=headers,
                             data=body_str.encode('utf-8'), timeout=30)
        return resp.json()
    except Exception as e:
        return {'status': 'failure', 'errorMessage': str(e)}


def odeme_baslat(clinic, plan_key, period, buyer_info, card_info, callback_url=None):
    plan = PLANS.get(plan_key)
    if not plan:
        return {'success': False, 'message': 'Geçersiz plan.'}

    price           = plan['yearly_total'] if period == 'yearly' else plan['monthly_price']
    conversation_id = f"dental-{clinic.clinic_id}-{uuid.uuid4().hex[:8]}"

    name    = buyer_info.get('name', 'Klinik')
    surname = buyer_info.get('surname', 'Sahibi')
    email   = buyer_info.get('email', 'test@test.com')
    phone   = buyer_info.get('phone', '+905000000000')
    city    = buyer_info.get('city', 'Istanbul')
    address = buyer_info.get('address', 'Turkiye')
    ip      = buyer_info.get('ip', '85.34.78.112')

    if not phone.startswith('+'):
        phone = f"+90{phone.replace(' ', '')}"

    payload = {
        "locale":         "tr",
        "conversationId": conversation_id,
        "price":          str(price),
        "paidPrice":      str(price),
        "currency":       "TRY",
        "installment":    "1",
        "basketId":       conversation_id,
        "paymentChannel": "WEB",
        "paymentGroup":   "SUBSCRIPTION",
        "paymentCard": {
            "cardHolderName": card_info.get('holder', ''),
            "cardNumber":     card_info.get('number', '').replace(' ', ''),
            "expireMonth":    card_info.get('exp_month', '12'),
            "expireYear":     card_info.get('exp_year', '2030'),
            "cvc":            card_info.get('cvc', ''),
            "registerCard":   "0",
        },
        "buyer": {
            "id":                  f"clinic-{clinic.clinic_id}",
            "name":                name,
            "surname":             surname,
            "gsmNumber":           phone,
            "email":               email,
            "identityNumber":      "11111111111",
            "registrationAddress": address,
            "ip":                  ip,
            "city":                city,
            "country":             "Turkey",
        },
        "shippingAddress": {
            "contactName": f"{name} {surname}",
            "city": city, "country": "Turkey", "address": address,
        },
        "billingAddress": {
            "contactName": f"{name} {surname}",
            "city": city, "country": "Turkey", "address": address,
        },
        "basketItems": [{
            "id":        f"{plan_key}-{period}",
            "name":      f"e-Randevu {plan['name']}",
            "category1": "Yazilim Aboneligi",
            "itemType":  "VIRTUAL",
            "price":     str(price),
        }],
    }

    result = _make_request('/payment/auth', payload)

    if result.get('status') == 'success':
        return {
            'success':         True,
            'payment_id':      result.get('paymentId'),
            'conversation_id': conversation_id,
            'message':         'Ödeme başarılı.',
        }
    else:
        return {
            'success':    False,
            'message':    result.get('errorMessage', 'Ödeme başarısız.'),
            'error_code': result.get('errorCode', ''),
        }