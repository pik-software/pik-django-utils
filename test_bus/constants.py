from datetime import datetime

from test_bus.serializers import TestRequestCommandSerializer


START_UNIX_EPOCH = datetime.utcfromtimestamp(0)
TEST_SERVICE = 'test_service'
TEST_ENTITY = 'TestEntity'
TEST_EXCHANGE = TEST_ENTITY
TEST_STATUS = 'accepted'

TEST_ENTITY_QUEUE = f'{TEST_SERVICE}.test_entity'
TEST_ENTITY_CONSUMES_SETTINGS = {
    TEST_ENTITY_QUEUE: TestEntitySerializer}

TEST_REQUEST_COMMAND_QUEUE = f'{TEST_SERVICE}.test_request_command'
TEST_REQUEST_COMMAND_CONSUMES_SETTINGS = {
    TEST_REQUEST_COMMAND_QUEUE: TestRequestCommandSerializer}

TEST_REQUESTS_SETTING = {
    'test_bus_local.models.TestRequestCommand': (
        'test_bus_local.models.TestResponseCommand',
        'test_bus_local.tasks.task_process_command')}

TEST_MDM_SERIALIZERS = [TestEntitySerializer]
