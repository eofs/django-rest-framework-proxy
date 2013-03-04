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
    'DEFAULT_HTTP_ACCEPT': 'application/json',
    'DEFAULT_HTTP_ACCEPT_LANGUAGE': 'en-US,en;q=0.8',
    'DEFAULT_CONTENT_TYPE': 'text/plain',

    # Return response as-is if enabled
    'RETURN_RAW': False,

    # Used to translate Accept HTTP field
    'ACCEPT_MAPS': {
        'text/html': 'application/json',
    },

    # Do not pass following parameters
    'DISALLOWED_PARAMS': ('format',),
    'MODEL_PARAM_MAP': {
        'PAGE': 'page',
        'PAGE_SIZE': 'page_size',
        'OFFSET': 'offset',
        'LIMIT': 'limit',
    }
}

api_proxy_settings = APISettings(USER_SETTINGS, DEFAULTS)
