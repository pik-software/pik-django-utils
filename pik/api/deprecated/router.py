from .viewsets import get_deprecated_viewset
from ..router import StandardizedRouter, StandardizedHiddenRouter


def get_mixin_class_by_function_name(viewset, function):
    for cls in viewset.__bases__:
        if hasattr(cls, function):
            if cls.__bases__ == (object, ):
                return cls
            return get_mixin_class_by_function_name(cls, function)


class DeprecatedRouterMixIn:
    def register(self, prefix, viewset, basename=None):
        viewset = get_deprecated_viewset(viewset)
        super().register(prefix, viewset, basename)

    # @staticmethod
    def get_history_viewset(self, viewset):
        history_viewset = get_deprecated_viewset(
            super().get_history_viewset(viewset))

        hook_mixin_class = get_mixin_class_by_function_name(
            viewset, 'deprecated_fields_render_hook')
        if hook_mixin_class is not None:
            history_viewset.__bases__ += (hook_mixin_class, )

        return history_viewset


class DeprecatedRouter(DeprecatedRouterMixIn, StandardizedRouter):
    pass


class HiddenDeprecatedRouter(DeprecatedRouterMixIn, StandardizedHiddenRouter):
    pass
