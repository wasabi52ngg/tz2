from django.shortcuts import render
from integration_utils.bitrix24.bitrix_user_auth.main_auth import main_auth
from django.conf import settings


@main_auth(on_start=True, set_cookie=True)
def start(request):
    """Стартовая страница для авторизации"""
    context = {}
    return render(request, 'start/start_page.html', context)