from rest_framework import permissions


class DjangoModelViewPermission(permissions.DjangoModelPermissions):

    perms_map = {**permissions.DjangoModelPermissions.perms_map,
                 **{'GET': ['%(app_label)s.view_%(model_name)s']}}

class CreateUpdateDjangoModelViewPermission(DjangoModelViewPermission):

    perms_map = {
        **permissions.DjangoModelPermissions.perms_map,
        'PUT': [
            '%(app_label)s.add_%(model_name)s',
            '%(app_label)s.change_%(model_name)s'
        ]
    }
