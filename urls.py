from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from main_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('app/', include('main_app.urls')),
    path('', include('start.urls')),
    path('product/<str:token>/', views.product_view_by_token, name='product_view_by_token'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
