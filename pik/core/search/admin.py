from pik.core.search.utils import (
    filter_queryset_by_search_index, check_search_config_consistency)


class SearchIndexAdminMixIn:
    SEARCH_INDEX_FIELD = 'search_index'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        check_search_config_consistency(self.model, self.search_fields)

    def has_search_index(self, request):  # noqa pylint: disable=arguments-differ
        if self.SEARCH_INDEX_FIELD in self.get_search_fields(request):
            return True
        return False

    def get_search_results(self, request, queryset, search_term):
        if self.has_search_index(request):
            use_distinct_flag = True
            queryset = filter_queryset_by_search_index(
                queryset, self.SEARCH_INDEX_FIELD, search_term)
            return queryset, use_distinct_flag
        return super().get_search_results(request, queryset, search_term)
