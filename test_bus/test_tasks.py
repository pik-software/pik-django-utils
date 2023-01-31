class TestMessageHandlerFetch:
    @staticmethod
    def test_default_handler_class():
        from pik.bus.tasks import handler_class  # noqa: import-outside-toplevel
        assert handler_class
