from django.urls import path
from . import views

app_name = 'main_app'

urlpatterns = [
    # Главная страница
    path('', views.index, name='index'),
    
    # Товары
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/sync/', views.sync_products, name='sync_products'),
    
    # QR-коды
    path('qr/generate/', views.qr_generate, name='qr_generate'),
    path('qr/result/<int:qr_link_id>/', views.qr_result, name='qr_result'),
    path('qr/list/', views.qr_list, name='qr_list'),
    
    
    # API
    path('api/product-search/', views.ProductSearchAPI.as_view(), name='product_search_api'),
]
