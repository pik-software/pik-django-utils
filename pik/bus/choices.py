from model_utils import Choices


REQUEST_COMMAND_STATUS_CHOICES = Choices(
    ('accepted', 'принято'),
    ('completed', 'выполнено'),
    ('failed', 'провал'))
