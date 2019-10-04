## SoftDeleted  docs

### Installation

- Upgrade pik-django-utils `pip install pik-django-utils>=1.0.23`

### Important notes

Current `pik-django-utils` guarantees (by default) all not SoftDeleted instances can't be deleted. Attempt to delete will raise an exception.
<b>Important info about integrations</b>: `history_type` on delete event will be <b>"~"</b>, not <b>"-"</b>.

### Settings `settings.py`

#### Safe mode `SOFT_DELETE_SAFE_MODE`

Default value: `True`<br><br>
If safe mode is on attempt to delete not SoftDeleted instance will raise an exception.
<br>
If you want some not SoftDeleted instances can be delete, you should add not softdeleted models to exclude list:
```python
SOFT_DELETE_EXCLUDE = (
    'auth.User',  # User model
    'app_nme.ModelName'
)
```

### Using

models.py

```python
class Organization(SoftDeleted, BaseHistorical):
    name = models.CharField(_('Наименование'), max_length=255)
    inn = models.CharField(
        _('ИНН'), max_length=10, validators=[inn_validator])
    kpp = models.CharField(
        _('КПП'), max_length=9, validators=[kpp_validator])
    is_actual = models.BooleanField(
        _('находится в периметре МСФО'), default=True)

    def __str__(self):
        return '{}'.format(self.name)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['inn', 'kpp'], condition=Q(deleted=None),
                name='unique_organization')
        ]
        ordering = ['-id']
        verbose_name = _('организация')
        verbose_name_plural = _('организации')
```

Shell:

```python
In [1]: organization = Organization.objects.create(name='АПИКА', inn='3562142312', kpp='447251097')

In [2]: Organization.objects.all()
Out[2]: <SoftOrganizationQuerySet [<Organization: АПИКА>]>

In [3]: organization.delete()
Out[3]: (0, {})

In [4]: Organization.objects.all()
Out[4]: <SoftOrganizationQuerySet []>

In [5]: Organization.all_objects.all()
Out[5]: <AllOrganizationQuerySet [<Organization: АПИКА>]>

In [6]: Organization.deleted_objects.all()
Out[6]: <SoftDeletedObjectsQuerySet [<Organization: АПИКА>]>

In [7]: Organization.objects.create(name='АПИКА', inn='3562142312', kpp='447251097')  # no IntegrityError
```

### Additional settings

If you want to use `QuerySet.as_manager()` you should do something like this:

#### Models
```python
from pik.core.models.soft_deleted import SoftObjectsQuerySet, AllObjectsQuerySet


class OrganizationQuerySet(models.QuerySet):
    @property
    def _has_unit_lookup(self):
        return Q(unit__id__isnull=False)

    def has_units(self):
        return self.filter(self._has_unit_lookup).distinct()

    def has_not_units(self):
        return self.exclude(self._has_unit_lookup).distinct()


class SoftOrganizationQuerySet(SoftObjectsQuerySet, OrganizationQuerySet):
    pass


class AllOrganizationQuerySet(AllObjectsQuerySet, OrganizationQuerySet):
    pass



class Organization(BaseHistorical):
    ...
    
    objects = SoftOrganizationQuerySet.as_manager()
    all_objects = AllOrganizationQuerySet.as_manager()

```

#### API

##### ViewSets
```python
class OrganizationViewSet(HistoryViewSetMixin, StandardizedModelViewSet):
    lookup_field = 'uid'
    lookup_url_kwarg = '_uid'
    ordering = '-id'
    serializer_class = OrganizationSerializer

    filter_backends = (
        StandardizedFieldFilters, StandardizedSearchFilter,
        StandardizedOrderingFilter,
    )
    filter_class = OrganizationFilter
    search_fields = ('name', 'uid', 'inn',)
    ordering_fields = ('name', 'updated',)

    def get_queryset(self):
        return Organization.all_objects.all()
```
##### Filters
```python
class EmploymentFilter(StandardizedFilterSet):
    organization = filters.RelatedFilter(
        OrganizationFilter,
        field_name='organization',
        queryset=Organization.all_objects.all())

    class Meta:
        model = Employment
        fields = {
            'uid': ['exact', 'isnull', 'in'],
            'updated': DATE_FILTERS,
            'created': DATE_FILTERS,
            'deleted': DATE_FILTERS
        }
```

##### M2M
```python
class UnitViewSet(HistoryViewSetMixin, StandardizedModelViewSet):
    lookup_field = 'uid'
    lookup_url_kwarg = '_uid'
    ordering = '-id'
    serializer_class = UnitSerializer

    filter_backends = (
        StandardizedFieldFilters, StandardizedSearchFilter,
        StandardizedOrderingFilter)
    filter_class = UnitFilter
    search_fields = ('name', 'unit_type__name', 'organization__name',
                     'organization__inn', 'organization__kpp',)
    ordering_fields = ('name', 'unit_type__name', 'updated', 'created')


    def get_queryset(self):
        return (Unit.all_objects.select_related(
            'unit_type', 'leader__unit_type', 'organization')
            .prefetch_related(
                Prefetch(
                    'buildings_group',
                    queryset=BuildingsGroup.all_objects.filter(
                        buildings_group_link__deleted__isnull=True).distinct()
                ),
            )
        )
```
```python
class SimpleUnitFilter(StandardizedFilterSet):
    buildings_group = filters.RelatedFilter(
        BuildingsGroupFilter, field_name='buildings_group',
        queryset=BuildingsGroup.all_objects.filter(
                        buildings_group_link__deleted__isnull=True).distinct())

    class Meta:
        model = Unit
        fields = {
            'name': NAME_FILTERS,
            'uid': ['exact', 'in'],
            'updated': DATE_FILTERS,
            'created': DATE_FILTERS,
            'deleted': DATE_FILTERS
        }
```