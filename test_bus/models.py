from django.db import models

from pik.core.models import BasePHistorical
from pik.bus.choices import REQUEST_COMMAND_STATUS_CHOICES as STATUSES


from pik.core.models.uided import PUided
from pik.core.models.dated import Dated
from pik.core.models.versioned import Versioned



class MyTestEntity(PUided, Dated, Versioned):
    pass


class MyTestRequestCommand(PUided, Dated, Versioned):
    requesting_service = models.CharField(max_length=255)


class MyTestResponseCommand(PUided, Dated, Versioned):
    request = models.ForeignKey(
        to=MyTestRequestCommand, on_delete=models.CASCADE)
    status = models.CharField(choices=STATUSES, max_length=255)
    error = models.CharField(max_length=255)
