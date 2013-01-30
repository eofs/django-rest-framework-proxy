from django.conf import settings

from rest_framework.settings import APISettings


USER_SETTINGS = getattr(settings, 'REST_PROXY', None)

DEFAULTS = {
    'HOST': None,
    'AUTH': {
        'user': None,
        'password': None,
    },
    'TIMEOUT': None,
}

api_proxy_settings = APISettings(USER_SETTINGS, DEFAULTS)
