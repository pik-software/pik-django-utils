class ConsumerError(Exception):
    pass


class QueuesMissingError(ConsumerError):
    pass


class SerializerMissingError(ConsumerError):
    pass


class ProducerError(Exception):
    pass


class ModelMissingError(ProducerError):
    pass


class MDMTransactionIsAlreadyStartedError(ProducerError):
    pass
