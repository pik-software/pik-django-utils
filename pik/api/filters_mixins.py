from abc import abstractmethod

from django.contrib.postgres.search import SearchQuery

from pik.core.search.constants import PG_SEARCH_RUSSIAN_LANGUAGE_CONFIG


class BaseStandardizedSearchIndexMixin:
    SEARCH_INDEX_FIELD = 'search_index'

    def get_search_index_queryset(self, queryset, value):
        if value:
            return queryset.filter(**{
                self.SEARCH_INDEX_FIELD:
                    SearchQuery(
                        value, config=PG_SEARCH_RUSSIAN_LANGUAGE_CONFIG)})
        return queryset

    @abstractmethod
    def is_search_index(self, *args):
        pass


class StandardizedAPISearchIndex(BaseStandardizedSearchIndexMixin):
    def is_search_index(self, request, view):  # noqa pylint: disable=arguments-differ
        search_fields = self.get_search_fields(view, request)
        return search_fields and self.SEARCH_INDEX_FIELD in search_fields

    def filter_queryset(self, request, queryset, view):
        if self.is_search_index(request, view):
            search_terms = ' '.join(self.get_search_terms(request))
            return self.get_search_index_queryset(queryset, search_terms)
        return super().filter_queryset(request, queryset, view)
