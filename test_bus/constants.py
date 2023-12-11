from datetime import datetime

from pik.bus.choices import REQUEST_COMMAND_STATUS_CHOICES as STATUSES


START_UNIX_EPOCH = datetime.utcfromtimestamp(0)
TEST_SERVICE = 'test_service'
TEST_ENTITY = 'TestEntity'
TEST_REQUEST_COMMAND = 'TestRequestCommand'
TEST_QUEUE4REQUEST_COMMAND = f'{TEST_SERVICE}.{TEST_REQUEST_COMMAND}'
TEST_QUEUE4ENTITY = f'{TEST_SERVICE}.{TEST_ENTITY}'
TEST_STATUS = STATUSES.accepted

TEST_RABBITMQ_CONSUMES4REQUEST_COMMAND = {
    TEST_QUEUE4REQUEST_COMMAND:
        'test_bus.serializers.MyTestRequestCommandSerializer'}

TEST_RABBITMQ_CONSUMES4ENTITY = {
    TEST_QUEUE4ENTITY:
        'test_bus.serializers.MyTestEntitySerializer'}

TEST_RABBITMQ_RESPONSES = {
    'test_bus.serializers.MyTestRequestCommandSerializer': (
        'test_bus.serializers.MyTestResponseCommandSerializer',
        'test_bus.tasks.exec_command')
}

TEST_RABBITMQ_PRODUCES = {
    'TestEntity': 'test_bus.serializers.MyTestEntitySerializer'}
