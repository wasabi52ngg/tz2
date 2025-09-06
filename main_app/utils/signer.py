"""
Утилиты для создания и проверки подписанных токенов
"""
import json
import hmac
import hashlib
import base64
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone


class TokenSigner:
    """Класс для создания и проверки подписанных токенов"""
    
    def __init__(self, secret_key=None):
        self.secret_key = secret_key or getattr(settings, 'SECRET_KEY', 'default-secret-key')
    
    def sign(self, data, expires_in_days=None):
        """
        Создать подписанный токен из данных
        
        Args:
            data (dict): Данные для подписи
            expires_in_days (int): Срок действия в днях (None = без ограничений)
        
        Returns:
            str: Подписанный токен в base64
        """
        # Добавляем время создания
        payload = {
            'data': data,
            'created_at': timezone.now().isoformat(),
        }
        
        # Добавляем срок действия если указан
        if expires_in_days:
            payload['expires_at'] = (timezone.now() + timedelta(days=expires_in_days)).isoformat()
        
        # Кодируем данные в JSON
        json_data = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        
        # Создаем подпись
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            json_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Объединяем данные и подпись
        token_data = f"{json_data}.{signature}"
        
        # Кодируем в base64
        return base64.urlsafe_b64encode(token_data.encode('utf-8')).decode('utf-8')
    
    def unsign(self, token):
        """
        Проверить и расшифровать токен
        
        Args:
            token (str): Подписанный токен
        
        Returns:
            dict: Данные из токена или None если токен невалиден
        """
        try:
            # Декодируем из base64
            token_data = base64.urlsafe_b64decode(token.encode('utf-8')).decode('utf-8')
            
            # Разделяем данные и подпись
            json_data, signature = token_data.rsplit('.', 1)
            
            # Проверяем подпись
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                json_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return None
            
            # Парсим JSON
            payload = json.loads(json_data)
            
            # Проверяем срок действия
            if 'expires_at' in payload:
                expires_at = datetime.fromisoformat(payload['expires_at'].replace('Z', '+00:00'))
                if timezone.now() > expires_at:
                    return None
            
            return payload['data']
            
        except (ValueError, json.JSONDecodeError, KeyError):
            return None
    
    def create_product_token(self, product_id, expires_in_days=365):
        """
        Создать токен для товара
        
        Args:
            product_id (int): ID товара
            expires_in_days (int): Срок действия в днях
        
        Returns:
            str: Подписанный токен
        """
        data = {
            'product_id': product_id,
            'type': 'product_view'
        }
        return self.sign(data, expires_in_days)
    
    def verify_product_token(self, token):
        """
        Проверить токен товара
        
        Args:
            token (str): Подписанный токен
        
        Returns:
            int: ID товара или None если токен невалиден
        """
        data = self.unsign(token)
        if data and data.get('type') == 'product_view':
            return data.get('product_id')
        return None


# Глобальный экземпляр для использования в приложении
signer = TokenSigner()
