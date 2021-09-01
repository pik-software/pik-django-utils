from ..camelcase.viewsets import get_camelcase_viewset
from ..router import StandardizedRouter, StandardizedHiddenRouter


class CamelCaseRouterMixIn:
    def register(self, prefix, viewset, basename=None):
        viewset = get_camelcase_viewset(viewset)
        super().register(prefix, viewset, basename)

    def get_history_viewset(self, viewset):
        return get_camelcase_viewset(super().get_history_viewset(viewset))


class CamelCaseRouter(CamelCaseRouterMixIn, StandardizedRouter):
    pass


class HiddenCamelCaseRouter(CamelCaseRouterMixIn, StandardizedHiddenRouter):
    pass
