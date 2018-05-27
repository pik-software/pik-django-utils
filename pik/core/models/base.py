from pik.core.models import Uided, Dated, Versioned, PUided, Historized


class BaseHistorical(Uided, Dated, Versioned, Historized):  # type: ignore
    class Meta:
        abstract = True


class BasePHistorical(PUided, Dated, Versioned, Historized):  # type: ignore
    class Meta:
        abstract = True
