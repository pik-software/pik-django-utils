from pik.core.models import Versioned


class MyVersioned(Versioned):
    pass


class MyStrictVersioned(Versioned):
    strict_autoincrement_version = True
