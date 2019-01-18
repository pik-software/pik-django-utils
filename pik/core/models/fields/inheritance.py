from django.db import models


class InheritPrimaryUidField(models.OneToOneField):
    """
    If you need to have a parent union class for many child sub-models with
    the same UID for the parent and child instances using models inheritance.

    For example, you have one model A and you want to divide a modal instance
    to different sub-models. Like divide Users to InternalUsers and
    ExternalUsers.

    Code:

        from pik.core.models import PUided

        class Users(PUided):
            pass

        class InternalUsers(Users):
            users_ptr = InheritPrimaryUidField(Users)

        class ExternalUsers(Users):
            users_ptr = InheritPrimaryUidField(Users)

    Now you can use InternalUsers, ExternalUsers and Users for ForeignKey

    # How it works in migrations? #

    For example, we have a model:

        class Foo(models.Model):
            models.ForeignKey(Users, on_delete=models.CASCADE)

    And change it to:

        class Foo(models.Model):
            models.ForeignKey(InternalUsers, on_delete=models.CASCADE)

    Case I: We have a Foo object in DB with FK to ExternalUsers which
    not included in InternalUsers. When we run `migrate` command we will
    catch error: `django.db.utils.IntegrityError` insert or update
    on table "app_foo" violates foreign key constraint ...

    Case II: We don't have such objects. It this case everything will correct.

    """
    def __init__(self, to, **kwargs):
        kwargs.update(dict(
            on_delete=models.CASCADE, parent_link=True,
            primary_key=True, to_field='uid',
        ))
        super().__init__(to, **kwargs)

    def get_pk_value_on_save(self, instance):
        return instance.uid
