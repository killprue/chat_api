import os
import datetime
import sys
import dj_database_url
import json
from django.core.exceptions import ImproperlyConfigured

CONFIG_FILE = 'config.json'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')

with open(os.path.join(BASE_DIR, CONFIG_FILE)) as config_file:
    configs = json.load(config_file)

def get_config(setting, configs=configs):
    try:
        return configs[setting]
    except KeyError:
        raise ImproperlyConfigured("Set the {} setting".format(setting))


SECRET_KEY = get_config('SECRET_KEY')
DEBUG = get_config('DEBUG')
REDIRECT_URL = get_config('REDIRECT_URL')
ADMIN_PATH = get_config('ADMIN_PATH')
ALLOWED_HOSTS = get_config("ALLOWED_HOSTS")


INSTALLED_APPS =[
    'channels',
    'daseiner.apps.DaseinerConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ORIGIN_ALLOW_ALL = False

CORS_ORIGIN_WHITELIST = get_config("CORS_ORIGINS")

ROOT_URLCONF = 'daseiner_proj.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'daseiner_proj.wsgi.application'
ASGI_APPLICATION = 'daseiner_proj.routing.application'


if get_config('DEBUG'):
    DATABASES = get_config('DATABASES')
    BROKER_URL = 'redis://localhost:6379'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379'
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts":[('127.0.0.1', 6379)]
            },
        },
    }
else:
    DATABASES = get_config("DATABASES")
    DATABASES['default'] = dj_database_url.config()
    BROKER_URL=os.environ['REDIS_URL']
    CELERY_RESULT_BACKEND=os.environ['REDIS_URL']    
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                "hosts": [
                    os.environ.get('REDIS_URL')],
            },
        },
    }
    CACHES = {
        "default": {
            "BACKEND": "redis_cache.RedisCache",
            "LOCATION": os.environ.get('REDIS_URL'),
        }
    }



AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'




EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = 'testing@testing.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

EMAIL_HOST = get_config('EMAIL_HOST')
EMAIL_HOST_USER = get_config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = get_config('EMAIL_HOST_PASSWORD')

CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Africa/Nairobi'
