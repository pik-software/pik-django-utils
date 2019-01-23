# pik-django-utils #

This project aim is to provide common django project utils and tools
for all PIK django projects.

It should provide guidance and tool recommendations for documentation,
testing, etc.

This project is a part of `django-service-boilerplate`.

## Versioning ##

We use semantic versioning MAJOR.MINOR.MAINTENANCE scheme, where the project author increments:

 - MAJOR version when they make incompatible API changes,
 - MINOR version when they add functionality in a backwards-compatible manner, and
 - MAINTENANCE version when they make backwards-compatible bug fixes.

# PACKAGES #

 - `pik.core` - Django specific staff
 - `pik.libs` - Django specific modules and libraries
 - `pik.utils` - not Django specific small utils and goodness

## pik.core ##

 - `pik.core.models` - Abstract Django models for common use cases
 - `pik.core.models.fields` - common model fields
 - `pik.core.tests` - Testing helpers
 - `pik.core.shortcuts` - Django code shortcuts and missed helpers
 - `pik.core.cache` - Cache helpers

### pik.core.models ###

 - `BasePHistorical` / `BaseHistorical` - Base Historical Entity models
 - `NullOwned` / `Owned` - Models for user relation
 - `SoftDeleted` - Soft deletable model

### pik.core.models.fields ###

 - `InheritPrimaryUidField` - Allows you to save the same UID Identifier for child table in inherited tables as in parent table

### pik.core.tests ###

 - `create_user` / `get_user` - user fixtures

### pik.core.shortcuts ###

 - `get_object_or_none(model: Type[models.Model], **search_keys) -> Optional[models.Model]`
 - `validate_and_create_object(model: Type[models.Model], **kwargs) -> models.Model`
 - `validate_and_update_object(obj: models.Model, **kwargs) -> Tuple[models.Model, bool]`
 - `update_or_create_object(model: Type[models.Model], search_keys: Optional[dict] = None, **kwargs) -> Tuple[models.Model, bool, bool]`
 - `get_current_request() -> Optional[HttpRequest]`

## pik.libs ##

...

## pik.utils ##

 - `pik.utils.normalization` - text normalization helpers

### pik.utils.normalization ###

 - `normalize(text: str) -> str`
 - `company_name_normalization(name: str) -> str`

---

 - [x] Follow https://packaging.python.org/
 - [x] Create `release.sh` file
 - [ ] Generate Django common settings
