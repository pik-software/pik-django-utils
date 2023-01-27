class TestMessageHandlerFetch:
    @staticmethod
    def test_default_handler_class():
        from pik.bus.tasks import handler_class
        assert handler_class
