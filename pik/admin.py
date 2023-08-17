from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from django.contrib.gis import admin


User = get_user_model()


class PermissionMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return '%s | %s | %s' % (  # noqa: consider-using-f-string
            obj.content_type.app_label, obj.content_type.model, obj.codename)


class ModelUserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'
        field_classes = {'user_permissions': PermissionMultipleChoiceField}


class ModelGroupAdminForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = '__all__'
        field_classes = {'permissions': PermissionMultipleChoiceField}


class ModelUserAdmin(UserAdmin):
    form = ModelUserAdminForm


class ModelGroupAdmin(GroupAdmin):
    form = ModelGroupAdminForm


def use_latin_permissions():
    # Re-register UserAdmin
    admin.site.unregister(User)
    admin.site.register(User, ModelUserAdmin)

    # don't show groups
    admin.site.unregister(Group)
    admin.site.register(Group, ModelGroupAdmin)
