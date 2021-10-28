from pik.core.search.utils import (
    filter_queryset_by_search_index, check_search_config_consistency)


class SearchIndexAPIFilterMixIn:
    SEARCH_INDEX_FIELD = 'search_index'

    def has_search_index(self, request, view):
        search_fields = self.get_search_fields(view, request)
        if search_fields and self.SEARCH_INDEX_FIELD in search_fields:
            return True
        return False

    def filter_queryset(self, request, queryset, view):
        if self.has_search_index(request, view):
            search_terms = ' '.join(self.get_search_terms(request))
            return filter_queryset_by_search_index(
                queryset, self.SEARCH_INDEX_FIELD, search_terms)
        return super().filter_queryset(request, queryset, view)


class SearchValidationViewSetMixIn:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        check_search_config_consistency(self.serializer_class.Meta.model,
                                        getattr(self, 'search_fields', []))
