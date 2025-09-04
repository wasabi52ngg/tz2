# Пример local_settings
# Измените данные на свои

DEBUG = True
ALLOWED_HOSTS = ['*']

from integration_utils.bitrix24.local_settings_class import LocalSettingsClass

# Настройки вашего приложения
# Добавьте здесь свои API ключи и настройки

APP_SETTINGS = LocalSettingsClass(
    portal_domain='your-portal.bitrix24.ru',
    app_domain='127.0.0.1:8000',
    app_name='PROJECT_NAME_PLACEHOLDER',
    salt='your-salt-key-here-change-this',
    secret_key='your-secret-key-here-change-this',
    application_bitrix_client_id='your-client-id',
    application_bitrix_client_secret='your-client-secret',
    application_index_path='/',
)

# Настройки базы данных
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'db_name',
        'USER': 'db_owner',
        'PASSWORD': 'password',
        'HOST': 'localhost',
    },
}
