from .uided import Uided, PUided
from .dated import Dated
from .versioned import Versioned
from .historized import Historized


class BaseHistorical(Uided, Dated, Versioned, Historized):  # type: ignore
    class Meta:
        ordering = ['created']
        abstract = True


class BasePHistorical(PUided, Dated, Versioned, Historized):  # type: ignore
    class Meta:
        ordering = ['created']
        abstract = True
