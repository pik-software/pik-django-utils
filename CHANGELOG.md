## 1.0.21 ##

### NEW ###

+ `pik.core.models.soft_deleted:` `AllObjectsQuerySet` now supports two queryset filters. It might be helpfull 
if you want to add filtering in your API not by `deleted` field, but on custom property (like `is_deleted`):
    + `is_deleted`. Example: `SomeModel.all_objects.is_deleted()`
    + `is_not_deleted`. Example: `SomeModel.all_objects.is_not_deleted()`

## 1.0.20 ##

### FIX ###

- `pik.core.models.soft_deleted:` made `SoftDeleted` model work correctly with history and auto_now fields

### NEW ###

- For now all not soft deletions are restricted by default. You can change it by setting `settings.SAFE_MODE` to `False`
- SoftDeleted models don't send `pre_delete` and `post_delete` signals

## 1.0.19 ##

### FIX ###

 - `pik.core.shortcuts.model_objects:` fix get m2m kwargs

## 1.0.18 ##

### FIX ###

 - sqlite3 tests issue
 - softdelete tests
 - `№` symbol noramilzation issue
 
 ### NEW ###
 
 - `validate_and_update_object` `validate_and_create_object` m2m support

## 1.0.17 ##

### FIX ###

 - `core.shortcuts`: get_object_or_none add QuerySet support
 - `core.shortcuts`: validate_and_update_object return updated fields list
 - `core.shortcuts`: update_or_create_object return updated fields list

### NOTE ###

 - validate_and_update_object, update_or_create_object -- changed return value !!

## 1.0.16 ##

 - django-simple-history>=2.4.0

## 1.0.15 ##

### NEW ###

 - `pik.core.models.fields`: InheritPrimaryUidField

## 1.0.14 ##

### NEW ###

 - `core.models.dated`: add indexes on `updated` and `created` fileds in `Dated` model

## 1.0.13 ##

### FIX ###

 - `pik.utils.normalization`: fix company_name_normalization

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
