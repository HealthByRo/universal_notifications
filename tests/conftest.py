# -*- coding: utf-8 -*-
def pytest_configure():
    from django.conf import settings
    from django.utils.translation import ugettext_lazy as _

    MIDDLEWARE = (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    )

    settings.configure(
        ADMINS=('foo@foo.com',),
        DEBUG_PROPAGATE_EXCEPTIONS=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:'
            }
        },
        SITE_ID=1,
        SECRET_KEY='not very secret in tests',
        USE_I18N=True,
        USE_L10N=True,
        STATIC_URL='/static/',
        ROOT_URLCONF='tests.urls',
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'APP_DIRS': True,
            },
        ],
        MIDDLEWARE=MIDDLEWARE,
        MIDDLEWARE_CLASSES=MIDDLEWARE,
        INSTALLED_APPS=(
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.staticfiles',
            'django.contrib.admin',
            'universal_notifications',
            'rest_framework',
            'rest_framework.authtoken',
            'tests',
        ),
        PASSWORD_HASHERS=(
            'django.contrib.auth.hashers.MD5PasswordHasher',
        ),
        REST_FRAMEWORK={
            'DEFAULT_VERSION': '1',
            'DEFAULT_PERMISSION_CLASSES': [
                'rest_framework.permissions.IsAuthenticated',
            ],
            'DEFAULT_AUTHENTICATION_CLASSES': (
                'rest_framework.authentication.TokenAuthentication',
            )

        },
        CELERY_APP_PATH='tests.celery.app',
        CELERY_TASK_ALWAYS_EAGER=True,
        UNIVERSAL_NOTIFICATIONS_TWILIO_ACCOUNT='fake',
        TESTING=True,

        # categories for notifications
        categories={
            "push": {
                "default":  _("This is a label for default category you'll send in from to FE"),
                "chat": _('Category for chat messages'),
                "promotions": _('Promotions',)
            },
            "email": {
                "default":  _("This is a label for default category you'll send in from to FE"),
                "chat": _('Category for chat messages'),
                "newsletter": _('Newsletter',)
            },
            "sms": {
                "default":  _("This is a label for default category you'll send in from to FE"),
                "chat": _('Category for chat messages'),
                "newsletter": _('Newsletter',)
            }
        },

        # user_categories_mapping={}
    )
