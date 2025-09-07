"""
Утилиты для создания и проверки подписанных токенов с Django TimestampSigner
"""
import json
from datetime import timedelta
from django.core.signing import TimestampSigner
from django.conf import settings


class TokenSigner:
    """Класс для создания и проверки подписанных токенов с Django TimestampSigner"""
    
    def __init__(self, secret_key=None):
        self.signer = TimestampSigner(key=secret_key or getattr(settings, 'SECRET_KEY', 'default-secret-key'))
    
    def create_product_token(self, product_id):
        data = {
            'product_id': product_id,
            'type': 'product_view'
        }
        
        json_data = json.dumps(data, ensure_ascii=False, sort_keys=True)
        
        return self.signer.sign(json_data)
    
    def verify_product_token(self, token):
        try:
            json_data = self.signer.unsign(token, max_age=timedelta(days=365))
            data = json.loads(json_data)
            
            if data.get('type') != 'product_view':
                return None
            
            return data.get('product_id')
            
        except Exception:
            return None


signer = TokenSigner()
