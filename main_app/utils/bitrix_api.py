"""
Утилиты для работы с API Битрикс24
"""
from django.conf import settings
from main_app.models import Product
from integration_utils.bitrix24.models import BitrixUserToken


class BitrixProductService:
    """Сервис для работы с товарами через integration_utils"""
    
    def __init__(self, user_token: BitrixUserToken):
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
        
        if detail_image:
            try:
                file_content = detail_image.read()
                import base64
                file_base64 = base64.b64encode(file_content).decode('utf-8')
                
                fields['DETAIL_PICTURE'] = {
                    'fileData': [detail_image.name, file_base64]
                }
                
                print(f"Изображение {detail_image.name} будет загружено в Битрикс24")
                
            except Exception as e:
                print(f"Ошибка при подготовке изображения для загрузки: {e}")

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
    
    def get_product_fields(self):
        """
        Получить список полей товара
        
        Returns:
            dict: Описание полей товара
        """
        return self.user_token.call_api_method('crm.product.fields')
    
    def sync_products_to_local(self, limit=50):
        """
        Синхронизировать товары из Битрикс24 в локальную базу
        
        Args:
            limit (int): Максимальное количество товаров для синхронизации
        
        Returns:
            tuple: (количество созданных, количество обновленных)
        """
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
            
            try:
                product = Product.objects.get(bitrix_id=bitrix_id)
                product.name = product_data.get('NAME', '')
                product.description = product_data.get('DESCRIPTION', '')
                product.price = float(product_data.get('PRICE', 0))
                product.currency = product_data.get('CURRENCY_ID', 'RUB')
                product.sort_order = int(product_data.get('SORT', 500))
                product.save()
                updated_count += 1
                
            except Product.DoesNotExist:
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