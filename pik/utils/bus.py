import time

from pika import BlockingConnection


class LiveBlockingConnection(BlockingConnection):
    """
    Subclassed from pika.BlockingConnection one
    with ability added to run periodic tasks (functions) as callbacks
    with periodic interval set (in seconds).
    """

    def __init__(self, parameters=None, _impl_class=None, *,
                 periodic_callback=None, periodic_callback_interval=None):
        super().__init__(parameters, _impl_class)
        self._live_callback = periodic_callback
        self._live_callback_interval = periodic_callback_interval
        self._deadline = self._set_next()

    def process_data_events(self, time_limit=None):
        if time_limit is None:
            time_limit = self._live_callback_interval
        self._run_callback()
        super().process_data_events(
            time_limit=time_limit)

    def _run_callback(self):
        if self._is_deadline_passed:
            try:
                self._live_callback()
            finally:
                self._set_next()

    @property
    def _is_deadline_passed(self):
        return time.monotonic() > self._deadline

    def _set_next(self):
        self._deadline = time.monotonic() + self._live_callback_interval
        return self._deadline
