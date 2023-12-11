from model_utils import Choices


REQUEST_COMMAND_STATUS_CHOICES = Choices(
    ('accepted', 'принято'),
    ('processing', 'обработка'),
    ('completed', 'выполнено'),
    ('failed', 'провал'))
