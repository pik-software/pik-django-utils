STANDARD_READ_ONLY_FIELDS = (
    'guid', 'type', 'version', 'updated', 'created',)
SOFT_DELETE_FIELDS = ('deleted', 'is_deleted',)

# API FILTERS
NAME_FILTERS = ['exact', 'in', 'startswith', 'endswith', 'contains']
DATE_FILTERS = ['exact', 'in', 'gt', 'gte', 'lt', 'lte']
