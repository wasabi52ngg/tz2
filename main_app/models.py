from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
import uuid


class Product(models.Model):
    """Модель товара, синхронизированная с Битрикс24"""
    
    # Основные поля
    bitrix_id = models.IntegerField(unique=True, verbose_name="ID в Битрикс24")
    name = models.CharField(max_length=255, verbose_name="Название товара")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        validators=[MinValueValidator(0)],
        verbose_name="Цена"
    )
    currency = models.CharField(max_length=3, default='RUB', verbose_name="Валюта")
    
    # Дополнительные поля
    photo_url = models.URLField(blank=True, null=True, verbose_name="URL фото")
    detail_image = models.ImageField(
        upload_to='products/', 
        blank=True, 
        null=True,
        verbose_name="Изображение товара"
    )
    sort_order = models.IntegerField(default=500, verbose_name="Порядок сортировки")
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return f"{self.name} (ID: {self.bitrix_id})"


class QRCodeLink(models.Model):
    """Модель для отслеживания сгенерированных QR-ссылок"""
    
    # Связи
    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE, 
        related_name='qr_links',
        verbose_name="Товар"
    )
    
    # Данные ссылки
    signed_token = models.TextField(unique=True, verbose_name="Подписанный токен")
    qr_code_image = models.ImageField(
        upload_to='qr_codes/', 
        blank=True, 
        null=True,
        verbose_name="Изображение QR-кода"
    )
    
    # Статистика использования
    access_count = models.PositiveIntegerField(default=0, verbose_name="Количество обращений")
    last_accessed = models.DateTimeField(blank=True, null=True, verbose_name="Последнее обращение")
    
    # Метаданные
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Срок действия")
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    
    class Meta:
        verbose_name = "QR-ссылка"
        verbose_name_plural = "QR-ссылки"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"QR для {self.product.name} (создана: {self.created_at.strftime('%d.%m.%Y %H:%M')})"
    
    def increment_access(self):
        """Увеличить счетчик обращений"""
        self.access_count += 1
        self.last_accessed = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed'])
    
    def is_expired(self):
        """Проверить, истекла ли ссылка"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
