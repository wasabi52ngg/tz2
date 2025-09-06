from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.core.paginator import Paginator
from integration_utils.bitrix24.bitrix_user_auth.main_auth import main_auth
from django.conf import settings
import json

from .models import Product, QRCodeLink
from .forms import ProductSearchForm, ProductCreateForm, QRCodeGenerateForm
from .utils.signer import signer
from .utils.qr_generator import create_qr_code_file, generate_product_qr_url
from .utils.bitrix_api import get_bitrix_api


@main_auth(on_cookies=True)
def index(request):
    """Главная страница приложения"""
    context = {}
    return render(request, 'main_app/index.html', context)


@main_auth(on_cookies=True)
def product_list(request):
    """Список товаров"""
    search_form = ProductSearchForm(request.GET)
    products = Product.objects.filter(is_active=True)
    
    if search_form.is_valid():
        search_type = search_form.cleaned_data['search_type']
        search_query = search_form.cleaned_data['search_query']
        
        if search_type == 'id':
            try:
                products = products.filter(bitrix_id=int(search_query))
            except ValueError:
                products = products.none()
        elif search_type == 'name':
            products = products.filter(name__icontains=search_query)
    
    # Пагинация
    paginator = Paginator(products.order_by('sort_order', 'name'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'search_form': search_form,
        'page_obj': page_obj,
        'products': page_obj,
    }
    return render(request, 'main_app/product_list.html', context)


@main_auth(on_cookies=True)
def product_create(request):
    """Создание товара в Битрикс24"""
    if request.method == 'POST':
        form = ProductCreateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                bitrix_id = form.save_to_bitrix(request.bitrix_user_token)
                
                # Создаем товар в локальной базе данных
                from .models import Product
                product, created = Product.objects.get_or_create(
                    bitrix_id=bitrix_id,
                    defaults={
                        'name': form.cleaned_data['name'],
                        'price': form.cleaned_data['price'],
                        'currency': form.cleaned_data['currency'],
                        'description': form.cleaned_data.get('description', ''),
                        'sort_order': 500,  # Значение по умолчанию
                    }
                )
                
                # Сохраняем изображение локально, если оно было загружено
                if form.cleaned_data.get('detail_image'):
                    product.detail_image = form.cleaned_data['detail_image']
                    product.save()
                
                messages.success(request, f'Товар успешно создан в Битрикс24 с ID: {bitrix_id}')
                return redirect('main_app:product_list')
            except Exception as e:
                messages.error(request, f'Ошибка создания товара: {str(e)}')
    else:
        form = ProductCreateForm()
    
    context = {
        'form': form,
    }
    return render(request, 'main_app/product_create.html', context)


@main_auth(on_cookies=True)
def qr_generate(request):
    """Генерация QR-кода для товара"""
    if request.method == 'POST':
        form = QRCodeGenerateForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            expires_in_days = form.cleaned_data['expires_in_days']
            
            try:
                # Создаем подписанный токен
                token = signer.create_product_token(product.id, expires_in_days)
                
                # Генерируем URL для QR-кода
                qr_url = generate_product_qr_url(token)
                
                # Создаем QR-код
                qr_file = create_qr_code_file(qr_url)
                
                # Сохраняем QR-ссылку в базе
                qr_link = QRCodeLink.objects.create(
                    product=product,
                    signed_token=token,
                    expires_at=signer.unsign(token) and signer.unsign(token).get('expires_at')
                )
                qr_link.qr_code_image.save(f"qr_{product.bitrix_id}_{qr_link.id}.png", qr_file, save=True)
                
                messages.success(request, 'QR-код успешно сгенерирован!')
                return redirect('main_app:qr_result', qr_link_id=qr_link.id)
                
            except Exception as e:
                messages.error(request, f'Ошибка генерации QR-кода: {str(e)}')
    else:
        form = QRCodeGenerateForm()
    
    context = {
        'form': form,
    }
    return render(request, 'main_app/qr_generate.html', context)


@main_auth(on_cookies=True)
def qr_result(request, qr_link_id):
    """Результат генерации QR-кода"""
    qr_link = get_object_or_404(QRCodeLink, id=qr_link_id)
    
    # Генерируем URL для отображения
    qr_url = generate_product_qr_url(qr_link.signed_token)
    
    context = {
        'qr_link': qr_link,
        'qr_url': qr_url,
    }
    return render(request, 'main_app/qr_result.html', context)


@main_auth(on_cookies=True)
def qr_list(request):
    """Список сгенерированных QR-кодов"""
    qr_links = QRCodeLink.objects.select_related('product').order_by('-created_at')
    
    # Пагинация
    paginator = Paginator(qr_links, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'qr_links': page_obj,
    }
    return render(request, 'main_app/qr_list.html', context)


def product_view_by_token(request, token):
    """Публичная страница товара по токену (без авторизации)"""
    # Проверяем токен
    product_id = signer.verify_product_token(token)
    if not product_id:
        raise Http404("Неверная или истекшая ссылка")
    
    # Получаем товар
    try:
        product = Product.objects.get(id=product_id, is_active=True)
    except Product.DoesNotExist:
        raise Http404("Товар не найден")
    
    # Получаем QR-ссылку для статистики
    try:
        qr_link = QRCodeLink.objects.get(signed_token=token, is_active=True)
        qr_link.increment_access()
    except QRCodeLink.DoesNotExist:
        qr_link = None
    
    context = {
        'product': product,
        'qr_link': qr_link,
    }
    return render(request, 'main_app/product_view.html', context)


@main_auth(on_cookies=True)
def sync_products(request):
    """Синхронизация товаров с Битрикс24"""
    if request.method == 'POST':
        try:
            from .utils.bitrix_api import BitrixProductService
            service = BitrixProductService(request.bitrix_user_token)
            created, updated = service.sync_products_to_local()
            messages.success(request, f'Синхронизация завершена. Создано: {created}, обновлено: {updated}')
        except Exception as e:
            messages.error(request, f'Ошибка синхронизации: {str(e)}')
    
    return redirect('main_app:product_list')


@method_decorator(csrf_exempt, name='dispatch')
class ProductSearchAPI(View):
    """API для поиска товаров (для автокомплита)"""
    
    def get(self, request):
        query = request.GET.get('q', '')
        if len(query) < 2:
            return JsonResponse({'results': []})
        
        products = Product.objects.filter(
            is_active=True,
            name__icontains=query
        ).values('id', 'bitrix_id', 'name', 'price')[:10]
        
        results = [
            {
                'id': p['id'],
                'bitrix_id': p['bitrix_id'],
                'name': p['name'],
                'price': str(p['price']),
                'text': f"{p['name']} (ID: {p['bitrix_id']}, {p['price']} руб.)"
            }
            for p in products
        ]
        
        return JsonResponse({'results': results})
