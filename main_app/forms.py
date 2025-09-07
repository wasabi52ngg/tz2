"""
Формы для приложения main_app
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Product
from .utils.bitrix_api import BitrixProductService


class ProductSearchForm(forms.Form):
    """Форма для поиска товара"""
    
    SEARCH_CHOICES = [
        ('id', 'Поиск по ID'),
        ('name', 'Поиск по названию'),
    ]
    
    search_type = forms.ChoiceField(
        choices=SEARCH_CHOICES,
        initial='name',
        widget=forms.RadioSelect,
        label='Тип поиска'
    )
    
    search_query = forms.CharField(
        max_length=255,
        label='Поисковый запрос',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ID товара или название...'
        })
    )
    
    def clean_search_query(self):
        """Валидация поискового запроса"""
        search_type = self.cleaned_data.get('search_type')
        search_query = self.cleaned_data.get('search_query')
        
        if search_type == 'id':
            try:
                int(search_query)
            except ValueError:
                raise ValidationError('ID товара должен быть числом')
        
        return search_query


class ProductCreateForm(forms.Form):
    """Форма для создания товара в Битрикс24"""
    
    name = forms.CharField(
        max_length=255,
        label='Название товара',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите название товара'
        })
    )
    
    price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        label='Цена',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '0.00'
        })
    )
    
    currency = forms.ChoiceField(
        choices=[
            ('RUB', 'Рубль (RUB)'),
            ('USD', 'Доллар (USD)'),
            ('EUR', 'Евро (EUR)'),
        ],
        initial='RUB',
        label='Валюта',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    description = forms.CharField(
        required=False,
        label='Описание',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Описание товара (необязательно)'
        })
    )
    
    
    detail_image = forms.ImageField(
        required=False,
        label='Изображение товара',
        help_text='Основное изображение товара',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    def save_to_bitrix(self, user_token):
        """Сохранить товар в Битрикс24"""
        if not user_token:
            raise ValidationError('Токен пользователя не найден')
        
        try:
            service = BitrixProductService(user_token)
            result = service.add_product(
                name=self.cleaned_data['name'],
                price=float(self.cleaned_data['price']),
                currency=self.cleaned_data['currency'],
                description=self.cleaned_data.get('description'),
                sort=500,
                detail_image=self.cleaned_data.get('detail_image')
            )
            
            if 'result' in result:
                return result['result']
            else:
                raise ValidationError(f"Ошибка создания товара: {result.get('error_description', 'Неизвестная ошибка')}")
                
        except Exception as e:
            raise ValidationError(f"Ошибка API: {str(e)}")


class QRCodeGenerateForm(forms.Form):
    """Форма для генерации QR-кода"""
    
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        empty_label="Выберите товар",
        label='Товар',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True).order_by('name')
