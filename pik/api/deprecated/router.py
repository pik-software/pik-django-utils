from .viewsets import get_deprecated_viewset
from ..router import StandardizedRouter, StandardizedHiddenRouter


class DeprecatedRouterMixIn:
    def register(self, prefix, viewset, basename=None):
        viewset = get_deprecated_viewset(viewset)
        super().register(prefix, viewset, basename)

    # @staticmethod
    def get_history_viewset(self, viewset):
        return get_deprecated_viewset(super().get_history_viewset(viewset))


class DeprecatedRouter(DeprecatedRouterMixIn, StandardizedRouter):
    pass


class HiddenDeprecatedRouter(DeprecatedRouterMixIn, StandardizedHiddenRouter):
    pass
