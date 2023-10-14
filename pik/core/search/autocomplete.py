from dal_select2.views import Select2QuerySetView
from django.contrib.auth.mixins import LoginRequiredMixin

from .utils import filter_queryset_by_search_index


class SearchIndexAutocompleteView(LoginRequiredMixin, Select2QuerySetView):
    SEARCH_INDEX_FIELD = 'search_index'
    select_related = ()
    forwarded_from = None

    def has_add_permission(self, request):
        return False

    def get_queryset(self):
        queryset = self.queryset

        if self.forwarded_from:
            forwarded = self.forwarded.get(self.forwarded_from)

            if forwarded:
                queryset = queryset.filter(
                    **{self.SEARCH_INDEX_FIELD: forwarded})

        queryset = filter_queryset_by_search_index(
            queryset, self.SEARCH_INDEX_FIELD, self.q)

        if self.select_related:
            queryset = queryset.select_related(*self.select_related)

        return queryset
