"""
Утилиты для генерации QR-кодов
"""
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings


def generate_qr_code(url, size=10, border=4):
    """
    Генерировать QR-код для URL
    
    Args:
        url (str): URL для кодирования
        size (int): Размер QR-кода (10 = 250x250px)
        border (int): Размер границы
    
    Returns:
        BytesIO: Поток с изображением QR-кода
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Создаем изображение
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Конвертируем в BytesIO
    img_buffer = BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return img_buffer


def create_qr_code_file(url, filename=None):
    """
    Создать файл QR-кода для сохранения в Django
    
    Args:
        url (str): URL для кодирования
        filename (str): Имя файла (опционально)
    
    Returns:
        ContentFile: Django файл с QR-кодом
    """
    qr_buffer = generate_qr_code(url)
    
    if not filename:
        # Генерируем имя файла на основе URL
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        filename = f"qr_{url_hash}.png"
    
    return ContentFile(qr_buffer.getvalue(), name=filename)


def generate_product_qr_url(token, base_url=None):
    """
    Генерировать URL для товара с токеном
    
    Args:
        token (str): Подписанный токен
        base_url (str): Базовый URL (по умолчанию localhost:8000)
    
    Returns:
        str: Полный URL для QR-кода
    """
    if not base_url:
        base_url = "http://localhost:8000"
    
    return f"{base_url}/product/{token}/"
