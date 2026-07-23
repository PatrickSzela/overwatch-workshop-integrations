from typing import Callable


class EventListener[**P]:
    def __init__(self):
        self._listeners: list[Callable[P, None]] = []

    def on(self, callback: Callable[P, None]):
        self._listeners.append(callback)

    def off(self, callback: Callable[P, None]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def emit(self, *args: P.args, **kwargs: P.kwargs):
        for listener in self._listeners:
            listener(*args, **kwargs)
