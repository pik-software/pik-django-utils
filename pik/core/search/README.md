# Full text search index

## Install

1. Add `SearchIndexField` to your model, with fields you have to be used as 
index source with `search_fields` argument:

    ```python
    from django.db import models
    from core.search.fields import SearchIndexField
    
    class Model(models.Model):
        first_name = models.CharField()
        last_name = models.CharField()
        search_index = SearchIndexField(search_fields=('first_name', 'last_name'))
    ```

2. Create migration

    ```bash
    ./manage.py makemigrations 
    
    Migrations for 'app':
      app/migrations/0002_auto.py
        - Add field search_index to app
    ```

3. Update migration to prefill `search_index` if you adding it to existing model

    ```diff
    
    import core.search.fields
    from django.db import migrations
    from core.search.utils import search_index_migration
    
    class Migration(migrations.Migration):
    
        dependencies = [
    +       ('search', '0001_create_unaccent_config'),
            ('app', '0071_auto'),
        ]
    
        operations = [
            migrations.AddField(
                model_name='model',
                name='search_index',
                field=core.search.fields.SearchIndexField(default='', search_fields=('first_name', 'last_name')),
            ),
    +       search_index_migration(app='app', model='Model')
        ]
    ``` 

4. Add ModelAdmin MixIn

    ```python
    from django.contrib import admin
    from core.search.admin import SearchIndexAdminMixIn
    
    class ModelAdmin(SearchIndexAdminMixIn, admin.ModelAdmin):
        pass
    ```

5. Add API Filter MixIn

    ```python
    from rest_framework.filters import SearchFilter
    from core.search.api import SearchIndexAPIFilterMixIn
    
    class StandardizedSearchFilter(SearchIndexAPIFilterMixIn, SearchFilter):
        pass
    ```


## Multiple search indexes

It is possible to define more than one search index, and they all will be 
filled out automatically. But if you want to use them in search, you have to 
override ModelAdmin and API Filter settings or implement multiple search index
logic yourself.

```python
class Model(models.Model):
    search_index = SearchIndexField(search_fields=('first_name', 'last_name'))
    custom_search_index = SearchIndexField(search_fields=('first_name', 'last_name', 'middle_name'))

class StandardizedSearchFilter(SearchIndexAPIFilterMixIn, SearchFilter):
    SEARCH_INDEX_FIELD = 'custom_search_index'

 
class ModelAdmin(SearchIndexAdminMixIn, admin.ModelAdmin):
    SEARCH_INDEX_FIELD = 'custom_search_index'
```
