import mercadopago
import logging
from typing import Dict, Any
import requests
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class MercadoPagoPIX:
    """Gerencia pagamentos PIX através do Mercado Pago."""
    
    def __init__(self, access_token: str):
        """Inicializa o SDK do Mercado Pago."""
        self.sdk = mercadopago.SDK(access_token)
        self.access_token = access_token
        
    def create_pix_payment(self, user_id: str, video_price: float,) -> Dict[str, Any]:
        """
        Cria um pagamento PIX.
        
        Args:
            user_id: ID do usuário
            video_price: Preço
            user_email: Email (opcional)
        
        Returns:
            Dict com dados do PIX
        """
        
         
        
        # Gera ID único
        idempotency_key = str(uuid.uuid4())
        
        # URL da API
        url = "https://api.mercadopago.com/v1/orders"
        
        # Headers
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": idempotency_key,
        }
        
        # Dados do pagamento
        order_data = {
            "type": "online",
            "external_reference": f"telegram_{user_id}_{int(datetime.now().timestamp())}",
            "total_amount": str(float(video_price)),
            "payer": {
                "email": "email",
                "first_name":f"User{user_id[:8]}",
            },
            "transactions": {
                "payments": [
                    {
                        "amount": str(float(video_price)),
                        "payment_method": {
                            "id": "pix",
                            "type": "bank_transfer"
                        }
                    }
                ]
            },
        }
        
        print(f"🚀 Criando PIX: R$ {video_price}")
        print(f"💰 Valor: R$ {video_price:.2f}")
        
        try:
            response = requests.post(url, headers=headers, json=order_data, timeout=30)
            
            print(f"📥 Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                order = response.json()
                print(f"✅ Resposta order: {order}")
                print(f"✅ Order criada! ID: {order.get('id')}")
                print(f"📊 Status: {order.get('status')}")
                
                # Extrai dados do PIX
                payments = order.get("transactions", {}).get("payments", [])
                if payments:
                    payment = payments[0]
                    payment_method = payment.get("payment_method", {})
                    
                    pix_code = payment_method.get("qr_code", "")
                    qr_base64 = payment_method.get("qr_code_base64", "")
                    ticket_url = payment_method.get("ticket_url", "")
                    pix = payment_method.get("id", "")
                    
                    return {
                        "success": True,
                        "data": {
                            "order_id": order.get('id'),
                            "created_date": order.get("created_date", ""),
                            "last_updated_date": order.get("last_updated_date", ""),
                            "date_of_expiration": payment.get("date_of_expiration"),
                            "payment_id": payment.get("id", ""),
                            "amount": payment.get("amount"),
                            "status": order.get("status", ""),
                            "status_detail": order.get("status_detail", ""),
                            "pix_code": pix_code,
                            "pix_qr_code_base64": qr_base64,
                            "ticket_url": ticket_url,
                            "payment_method": pix,
                            "external_reference": order.get("external_reference", ""),
                            "full_response": order
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Nenhum pagamento na order"
                    }
            else:
                error_msg = response.text
                print(f"❌ Erro: {error_msg}")
                
                return {
                    "success": False,
                    "error": f"Status {response.status_code}: {error_msg}",
                }
                
        except Exception as e:
            print(f"❌ Exceção: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_payment_status(self, order_id: str) -> Dict[str, Any]:
        """Verifica o status de uma order."""

        print(f"✅ Order ID:{order_id}")
        try:
            url = f"https://api.mercadopago.com/v1/orders/{order_id}"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            print(f"🔍 Verificando order: {order_id}")
            print(f"🔑 Token: {self.access_token[:15]}...")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            print(f"📥 Status: {response.status_code}")
            
            if response.status_code == 200:
                order = response.json()
                print(f"✅ Resposta order: {order}")
                print(f"✅ Order encontrada: {order.get('id')}")
                print(f"📊 Status: {order.get('status')}")
                
                # Verifica se há pagamentos
                payments = order.get("transactions", {}).get("payments", [])
                if payments:
                    payment = payments[0]
                    print(f"💳 Payment status: {payment.get('status')}")
                    
                    return {
                        "success": True,
                        "data": {
                            "order_id": order["id"],
                            "created_date": order.get("created_date", ""),
                            "last_updated_date": order.get("last_updated_date", ""),
                            "date_of_expiration": payment.get("date_of_expiration"),
                            "order_status": order.get("status", ""),
                            "payment_id": payment.get("id", ""),
                            "status": payment.get("status", ""),
                            "status_detail": payment.get("status_detail", ""),
                            "paid_amount": payment.get("paid_amount"),
                            "external_reference": order.get("external_reference", "")
                        }
                    }
                else:
                    print("⚠️ Nenhum pagamento na order")
                    return {
                        "success": True,
                        "order_id": order["id"],
                        "order_status": order.get("status", ""),
                        "payment_id": "",
                        "payment_status": "no_payment",
                    }
            else:
                error_text = response.text[:200] if response.text else "Sem resposta"
                print(f"❌ Erro: {response.status_code} - {error_text}")
                
                return {
                    "success": False,
                    "error": f"Status {response.status_code}: {error_text}",
                    "status_code": response.status_code
                }
                
        except Exception as e:
            print(f"❌ Exceção: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "success": False,
                "error": str(e)
            }
        
    def test_order_exists(self, order_id: str) -> bool:
        """Testa se uma order existe no Mercado Pago."""
        try:
            url = f"https://api.mercadopago.com/v1/orders/{order_id}"
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except:
            return False