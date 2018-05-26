from django.db import models
from django.db.models import F


class Versioned(models.Model):
    autoincrement_version = True

    # Strict increment leads to problems in SimpleHistory (disable by default)
    strict_autoincrement_version = False

    version = models.IntegerField(editable=False)

    def save(self, *args, **kwargs):  # noqa: pylint=arguments-differ
        if not self.version:
            self.version = 1
        else:
            if self.autoincrement_version and self.pk:
                self.version = F('version') + 1 \
                    if self.strict_autoincrement_version \
                    else self.version + 1

        super().save(*args, **kwargs)

    def optimistic_concurrency_update(self, **kwargs):
        """
        Safe optimistic concurrent update. If the object was not modified
        since we fetched it than the object is updated and function will
        return `True`. If it was modified than the function will
        return `False` and the object will not be updated.

        NOTE 1: In an environment with a lot of concurrent updates
        this approach might be wasteful.

        NOTE 2: This approach does not protect from modifications made
        to the object outside this function. If you have other tasks
        that modify the data directly (e.g use `save()` directly)
        you need to make sure they use the version as well.

        Example:

            class Account(Versioned):
                balance = models.IntegerField(default=100)

                def withdraw(self, amount):
                    if self.balance < amount:
                        raise errors.RuntimeError()

                    result = self.balance - amount
                    return self.optimistic_concurrency_update(balance=balance)

            x = Account()
            x.withdraw(100)
            x.withdraw(100)

        :return: is the object updated
        :rtype: bool
        """
        # more detail here: https://medium.com/@hakibenita/how-to-manage-concurrency-in-django-models-b240fed4ee2  # noqa
        kwargs['version'] = self.version + 1
        model = type(self)
        updated = model.objects.filter(pk=self.pk, version=self.version) \
            .update(**kwargs)
        # TODO: trigger post_save event
        return updated > 0

    class Meta:
        abstract = True
