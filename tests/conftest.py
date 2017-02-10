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
        TESTING=True,

        UNIVERSAL_NOTIFICATIONS_TWILIO_ACCOUNT='fake',
        # categories for notifications
        UNIVERSAL_NOTIFICATIONS_CATEGORIES={
            "push": {
                "default": _("This is a label for default category you'll send in from to FE"),
                "chat": _('Category for chat messages'),
                "promotions": _('Promotions',)
            },
            "email": {
                "default": _("This is a label for default category you'll send in from to FE"),
                "chat": _('Category for chat messages'),
                "newsletter": _('Newsletter',)
            },
            "sms": {
                "default": _("This is a label for default category you'll send in from to FE"),
                "chat": _('Category for chat messages'),
                "newsletter": _('Newsletter',)
            },
            "test": {
                "default": _("This is a label for default category you'll send in from to FE"),
            },
        },
        # not required. If defined, specific types of users will only get notifications from allowed categories.
        # requires a bit more configuration - helper function to check if notification category is allowed for user
        UNIVERSAL_NOTIFICATIONS_USER_CATEGORIES_MAPPING={
            "for_admin": {
                "push": ["default", "chat", "promotions"],
                "email": ["default", "chat", "newsletter"],
                "sms": ["default", "chat", "newsletter"]
            },
            "for_user": {
                "push": ["default", "chat", "promotions"],
                "email": ["default", "newsletter"],  # chat skipped
                "sms": ["default", "chat", "newsletter"]
            }
        },
        # path to the file we will import user definitions for UNIVERSAL_NOTIFICATIONS_USER_CATEGORIES_MAPPING
        UNIVERSAL_NOTIFICATIONS_USER_DEFINITIONS_FILE='tests.user_conf'
    )
