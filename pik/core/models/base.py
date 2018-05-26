from pik.core.models import Uided, Dated, Versioned, PUided, Historized


class BaseHistorical(Uided, Dated, Versioned, Historized):
    class Meta:
        abstract = True


class BasePHistorical(PUided, Dated, Versioned, Historized):
    class Meta:
        abstract = True
