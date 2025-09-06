"""
Утилиты для работы с API Битрикс24
"""
import requests
import json
from django.conf import settings
from main_app.models import Product


class BitrixAPI:
    """Класс для работы с API Битрикс24"""
    
    def __init__(self, webhook_url=None, user_id=None):
        self.webhook_url = webhook_url or getattr(settings, 'BITRIX_WEBHOOK_URL', None)
        self.user_id = user_id or getattr(settings, 'BITRIX_USER_ID', None)
        
        if not self.webhook_url or not self.user_id:
            raise ValueError("Необходимо указать BITRIX_WEBHOOK_URL и BITRIX_USER_ID в настройках")
    
    def _make_request(self, method, params=None):
        """
        Выполнить запрос к API Битрикс24
        
        Args:
            method (str): Название метода API
            params (dict): Параметры запроса
        
        Returns:
            dict: Ответ API
        """
        url = f"{self.webhook_url}/rest/{self.user_id}/{method}"
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        data = params or {}
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Ошибка API Битрикс24: {e}")
    
    def _upload_file(self, file_obj, filename):
        """
        Загрузить файл в Битрикс24
        
        Args:
            file_obj: Файловый объект
            filename (str): Имя файла
        
        Returns:
            dict: Результат загрузки с ID файла
        """
        url = f"{self.webhook_url}/rest/{self.user_id}/disk.folder.uploadfile"
        
        files = {
            'file': (filename, file_obj, 'image/jpeg')
        }
        
        data = {
            'id': 'shared_files'  # Загружаем в общую папку
        }
        
        try:
            response = requests.post(url, files=files, data=data, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Ошибка загрузки файла в Битрикс24: {e}")
    
    def add_product(self, name, price, currency='RUB', description=None, sort=500, detail_image=None):
        """
        Добавить товар в Битрикс24
        
        Args:
            name (str): Название товара
            price (float): Цена товара
            currency (str): Валюта (по умолчанию RUB)
            description (str): Описание товара
            sort (int): Порядок сортировки
            detail_image: Файл изображения товара
        
        Returns:
            dict: Результат создания товара
        """
        fields = {
            'NAME': name,
            'CURRENCY_ID': currency,
            'PRICE': price,
            'SORT': sort
        }
        
        if description:
            fields['DESCRIPTION'] = description
        
        # Загружаем изображение товара
        if detail_image:
            try:
                image_result = self._upload_file(detail_image, f"{name}.jpg")
                if 'result' in image_result:
                    fields['DETAIL_PICTURE'] = image_result['result']['ID']
            except Exception as e:
                print(f"Ошибка загрузки изображения товара: {e}")
        
        return self._make_request('crm.product.add', {'fields': fields})
    
    def get_products(self, filter_params=None, select_fields=None, order=None):
        """
        Получить список товаров из Битрикс24
        
        Args:
            filter_params (dict): Параметры фильтрации
            select_fields (list): Поля для выборки
            order (dict): Параметры сортировки
        
        Returns:
            dict: Список товаров
        """
        params = {}
        
        if filter_params:
            params['filter'] = filter_params
        
        if select_fields:
            params['select'] = select_fields
        
        if order:
            params['order'] = order
        
        return self._make_request('crm.product.list', params)
    
    def get_product_fields(self):
        """
        Получить список полей товара
        
        Returns:
            dict: Описание полей товара
        """
        return self._make_request('crm.product.fields')
    
    def sync_products_to_local(self, limit=50):
        """
        Синхронизировать товары из Битрикс24 в локальную базу
        
        Args:
            limit (int): Максимальное количество товаров для синхронизации
        
        Returns:
            tuple: (количество созданных, количество обновленных)
        """
        # Получаем товары из Битрикс24
        response = self.get_products(
            select_fields=['ID', 'NAME', 'DESCRIPTION', 'PRICE', 'CURRENCY_ID', 'SORT'],
            order={'NAME': 'ASC'}
        )
        
        if 'result' not in response:
            raise Exception("Неверный ответ API Битрикс24")
        
        products = response['result']
        created_count = 0
        updated_count = 0
        
        for product_data in products[:limit]:
            bitrix_id = int(product_data['ID'])
            
            # Проверяем, существует ли товар
            try:
                product = Product.objects.get(bitrix_id=bitrix_id)
                # Обновляем существующий товар
                product.name = product_data.get('NAME', '')
                product.description = product_data.get('DESCRIPTION', '')
                product.price = float(product_data.get('PRICE', 0))
                product.currency = product_data.get('CURRENCY_ID', 'RUB')
                product.sort_order = int(product_data.get('SORT', 500))
                product.save()
                updated_count += 1
                
            except Product.DoesNotExist:
                # Создаем новый товар
                Product.objects.create(
                    bitrix_id=bitrix_id,
                    name=product_data.get('NAME', ''),
                    description=product_data.get('DESCRIPTION', ''),
                    price=float(product_data.get('PRICE', 0)),
                    currency=product_data.get('CURRENCY_ID', 'RUB'),
                    sort_order=int(product_data.get('SORT', 500))
                )
                created_count += 1
        
        return created_count, updated_count


# Глобальный экземпляр для использования в приложении
def get_bitrix_api():
    """Получить экземпляр API Битрикс24"""
    try:
        return BitrixAPI()
    except ValueError:
        # Возвращаем None если настройки не заданы
        return None


class BitrixProductService:
    """Сервис для работы с товарами через integration_utils"""
    
    def __init__(self, user_token):
        self.user_token = user_token
    
    def add_product(self, name, price, currency='RUB', description=None, sort=500, detail_image=None):
        """
        Добавить товар в Битрикс24
        
        Args:
            name (str): Название товара
            price (float): Цена товара
            currency (str): Валюта (по умолчанию RUB)
            description (str): Описание товара
            sort (int): Порядок сортировки
            detail_image: Файл изображения товара
        
        Returns:
            dict: Результат создания товара
        """
        fields = {
            'NAME': name,
            'CURRENCY_ID': currency,
            'PRICE': price,
            'SORT': sort
        }
        
        if description:
            fields['DESCRIPTION'] = description
        
        # TODO: Добавить поддержку загрузки изображений
        # Пока что изображения не загружаются в Битрикс24
        if detail_image:
            print(f"Изображение {detail_image.name} будет сохранено локально, но не загружено в Битрикс24")
        
        return self.user_token.call_api_method('crm.product.add', {'fields': fields})
    
    def get_products(self, filter_params=None, select_fields=None, order=None):
        """
        Получить список товаров из Битрикс24
        
        Args:
            filter_params (dict): Параметры фильтрации
            select_fields (list): Поля для выборки
            order (dict): Параметры сортировки
        
        Returns:
            dict: Список товаров
        """
        params = {}
        
        if filter_params:
            params['filter'] = filter_params
        
        if select_fields:
            params['select'] = select_fields
        
        if order:
            params['order'] = order
        
        return self.user_token.call_api_method('crm.product.list', params)
    
    def sync_products_to_local(self, limit=50):
        """
        Синхронизировать товары из Битрикс24 в локальную базу
        
        Args:
            limit (int): Максимальное количество товаров для синхронизации
        
        Returns:
            tuple: (количество созданных, количество обновленных)
        """
        # Получаем товары из Битрикс24
        response = self.get_products(
            select_fields=['ID', 'NAME', 'DESCRIPTION', 'PRICE', 'CURRENCY_ID', 'SORT'],
            order={'NAME': 'ASC'}
        )
        
        if 'result' not in response:
            raise Exception("Неверный ответ API Битрикс24")
        
        products = response['result']
        created_count = 0
        updated_count = 0
        
        for product_data in products[:limit]:
            bitrix_id = int(product_data['ID'])
            
            # Проверяем, существует ли товар
            try:
                product = Product.objects.get(bitrix_id=bitrix_id)
                # Обновляем существующий товар
                product.name = product_data.get('NAME', '')
                product.description = product_data.get('DESCRIPTION', '')
                product.price = float(product_data.get('PRICE', 0))
                product.currency = product_data.get('CURRENCY_ID', 'RUB')
                product.sort_order = int(product_data.get('SORT', 500))
                product.save()
                updated_count += 1
                
            except Product.DoesNotExist:
                # Создаем новый товар
                Product.objects.create(
                    bitrix_id=bitrix_id,
                    name=product_data.get('NAME', ''),
                    description=product_data.get('DESCRIPTION', ''),
                    price=float(product_data.get('PRICE', 0)),
                    currency=product_data.get('CURRENCY_ID', 'RUB'),
                    sort_order=int(product_data.get('SORT', 500))
                )
                created_count += 1
        
        return created_count, updated_count
