from pik.core.models.uided import Uided, PUided
from pik.core.models.dated import Dated
from pik.core.models.versioned import Versioned
from pik.core.models.historized import Historized


class BaseHistorical(Uided, Dated, Versioned, Historized):  # type: ignore
    class Meta:
        abstract = True


class BasePHistorical(PUided, Dated, Versioned, Historized):  # type: ignore
    class Meta:
        abstract = True
