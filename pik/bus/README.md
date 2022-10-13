# MDM Bus integration


## Settings

| Param                    | Example                                                                             | Description                                            |
|--------------------------|-------------------------------------------------------------------------------------|--------------------------------------------------------|
| RABBITMQ_URL             | `amqp://username:password@host:5672`                                                | Amqp Url for amqp server for consumer & producer       |
| RABBITMQ_PRODUCER_ENABLE | `True`                                                                              | Enable amqp producer                                   |
| RABBITMQ_PRODUCES        | `{'ExploitationBuilding': 'housing.api_v1.serializers.BuildingSerializer'}`         | Dict of exchanges and serializers for produced entities|
| RABBITMQ_CONSUMER_ENABLE | `True`                                                                              | Enable amqp consumer                                   |
| RABBITMQ_CONSUMES        | `{'ds-back.ExploitationBuilding': 'housing.api_v1.serializers.BuildingSerializer'}`<br><br/> | Dict of queues and serializers for consumable entities |
| BUS_EVENT_LOGSTASH_URL   | `https://username:password@host:1024`                                               | Logstash Url for mdm events logging                    |


## Consumer

```bash
./manage.py run_rabbitmq_consumer --skip-checks
```


## Model `pik.bus.models.PIKMessageException`

Model for storing failed processing messages, including missing dependencies.
Each time message successfully proceed, consumer searches for its dependants
and reproduces them too.

| Param             | Example                                                            | Description                                       |
|-------------------|--------------------------------------------------------------------|---------------------------------------------------|
| entity_uid        | `a3261b87-7dca-48bf-ab44-e9bd98cb2f12`                             | Failed message entity guid if possible to extract |
| queue             | `ds-back.ExploitationBuilding`                                     | Enable amqp producer                              |
| message           | `b'{...}'`                                                         | Message binary                                    |
| exception         | `{'code': 'invalid', 'detail': {'name': 'Too short'}}`             | Error message in `pik-django-urls` json format    |
| exception_type    | `invalid`                                                          | Internal error code                               |
| exception_message | `Invalid input.`                                                   | Error message text                                |
| dependencies      | `{'ExploitationBuilding': 'a3261b87-7dca-48bf-ab44-e9bd98cb2f12'}` | Message dependencies if some and are extractable  |
| has_dependencies  | `False`                                                            | Missing dependencies boolean flag                 |
