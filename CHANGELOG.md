## 1.0.13 ##

 - nothing changed yet

## 1.0.12 ##

 - Django>=1.11.15
 - celery>=4.2.1
 - kombu>=4.2.1

## 1.0.11 ##

 - flake8==3.5.0

### FIX ###

 - `core.models.dated`: fix verbose_name

## 1.0.10 ##

### FIX ###

 - `pik.utils.normalization`: fix bug with autocorrect 'Й' to 'И' and 'Ё' to 'Е'

## 1.0.9 ##

 - Django==1.11.15

## 1.0.8 ##

### NEW ###

 - `core.shortcuts`: get_current_request()

## 1.0.7 ##

### FIX ###

 - `core.shortcuts`: fix validate_and_update_object() to revert object changes on validation fail

### NEW ###

 - `core.shortcuts`: get_current_request()

## 1.0.6 ##

### FIX ###

 - `core.models`: change ugettext to ugettext_lazy

## 1.0.5 ##

### NEW ###

 - `core.cache`: @cachedmethod(key: str, ttl: int = 5 * 60, cachename: str = 'default')

## 1.0.4 ##

### NEW ###

 - `core.models`: BasePHistorical, BaseHistorical, NullOwned, Owned, SoftDeleted
 - `core.tests`: create_user(username, password, **kwargs), get_user(username)
 - `core.shortcuts`: get_object_or_none(model, **search_keys), validate_and_create_object(model, **kwargs), validate_and_update_object(model, search_keys=None, **kwargs), update_or_create_object(models, search_keys=None, **kwargs)

## 1.0.3 ##

### NEW ###

 - `utils.normalization`: normalize(text), company_name_normalization(name)

## 1.0.0 ##

 - nothing here
