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
