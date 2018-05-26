from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.utils.module_loading import import_string


def create_user(username=None, password=None, **kwargs):
    factory_class = getattr(settings, 'USER_FACTORY_CLASS', '')
    try:
        factory = import_string(factory_class)
        user = factory.create(**kwargs)
        if password:
            user.set_password(password)
            user.save()
        return user
    except ImportError:
        pass

    User = get_user_model()  # noqa: pylint=invalid-name
    if username is None:
        username = kwargs.get(User.USERNAME_FIELD)

    if not username:
        username = get_random_string()

    kwargs.update({
        User.USERNAME_FIELD: username,
    })

    user = User.objects.create(**kwargs)
    if password:
        user.set_password(password)
        user.save()
    return user


def get_user(username=None):  # noqa: pylint=invalid-name
    User = get_user_model()  # noqa: pylint=invalid-name
    return User._default_manager.get_by_natural_key(username)  # noqa
