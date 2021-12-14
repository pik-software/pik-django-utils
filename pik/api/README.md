## TypeFieldHook

It is required to have different type field values for camelcase and deprecated
api's. To acheave it there are two hooks in serializers:

- `deprecated_type_field_hook`,
- `camelcase_type_field_hook`.


```python

class BuildingSerializer(StandardizedSerializer):

    ...
    
    @staticmethod
    def deprecated_type_field_hook(*args, **kwargs):
        return 'BuildingSerializer'
    
    @staticmethod
    def camelcase_type_field_hook(*args, **kwargs):
        return 'ExplotationBuildingSerializer'
    

```
