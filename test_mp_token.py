#!/usr/bin/env python3
import os
import json
from dotenv import load_dotenv
import requests

load_dotenv()

token = os.getenv('MERCADO_PAGO_TOKEN')

if not token:
    print("❌ Token não encontrado")
    exit()

print(f"🔑 Token: {token[:20]}...")
print(f"📦 Testando NOVA API de Orders...")

url = "https://api.mercadopago.com/v1/orders"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "X-Idempotency-Key": "test-" + str(os.urandom(8).hex())
}

data = {
    "type": "online",
    "total_amount": "1.00",
    "external_reference": "test_123",
    "processing_mode": "automatic",
    "transactions": {
        "payments": [
            {
                "amount": "1.00",
                "payment_method": {
                    "id": "pix",
                    "type": "bank_transfer"
                },
                "expiration_time": "PT30M"
            }
        ]
    },
    "payer": {
        "email": "test@testuser.com"
    }
}

try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    print(f"📥 Status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        result = response.json()
        print("✅ SUCESSO! Order criada.")
        print(f"   Order ID: {result.get('id')}")
        print(f"   Status: {result.get('status')}")
        
        # Extrai dados PIX
        payments = result.get("transactions", {}).get("payments", [])
        if payments:
            pix_data = payments[0].get("payment_method", {})
            print(f"   QR Code: {pix_data.get('qr_code', '')[:50]}...")
            print(f"   Ticket URL: {pix_data.get('ticket_url', '')}")
    else:
        print(f"❌ Erro: {response.text}")
        
except Exception as e:
    print(f"❌ Exceção: {e}")