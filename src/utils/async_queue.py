import asyncio


class AsyncQueue[T]:
    def __init__(self):
        self._is_on = True
        self._queue: list[T] = []
        self._cond = asyncio.Condition()
        self._unfinished_tasks = 0
        self._finished = asyncio.Event()
        self._finished.set()

    def __contains__(self, item: T) -> bool:
        return item in self._queue

    def empty(self) -> bool:
        return len(self._queue) == 0

    def qsize(self) -> int:
        return len(self._queue)

    async def put(self, item: T) -> None:
        async with self._cond:
            if not self._is_on:
                raise RuntimeError("Queue is shut down")

            self._queue.append(item)
            self._unfinished_tasks += 1
            self._finished.clear()
            self._cond.notify()

    def put_nowait(self, item: T) -> None:
        if not self._is_on:
            raise RuntimeError("Queue is shut down")

        self._queue.append(item)
        self._unfinished_tasks += 1
        self._finished.clear()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():

            async def _notify():
                async with self._cond:
                    self._cond.notify()

            loop.create_task(_notify())

    async def insert(self, index: int, item: T) -> None:
        async with self._cond:
            if not self._is_on:
                raise RuntimeError("Queue is shut down")

            self._queue.insert(index, item)
            self._unfinished_tasks += 1
            self._finished.clear()
            self._cond.notify()

    def insert_nowait(self, index: int, item: T) -> None:
        if not self._is_on:
            raise RuntimeError("Queue is shut down")

        self._queue.insert(index, item)
        self._unfinished_tasks += 1
        self._finished.clear()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():

            async def _notify():
                async with self._cond:
                    self._cond.notify()

            loop.create_task(_notify())

    async def remove(self, item: T) -> None:
        async with self._cond:
            if item in self._queue:
                self._queue.remove(item)
                self.task_done()
                self._cond.notify()

    def remove_nowait(self, item: T) -> None:
        if item in self._queue:
            self._queue.remove(item)
            self.task_done()

    async def get(self) -> T:
        async with self._cond:
            while not self._queue:
                if not self._is_on:
                    raise RuntimeError("Queue is shut down")
                await self._cond.wait()
            return self._queue.pop(0)

    def task_done(self) -> None:
        if self._unfinished_tasks <= 0:
            raise ValueError("task_done() called too many times")

        self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._finished.set()

    async def join(self) -> None:
        if self._unfinished_tasks > 0:
            await self._finished.wait()

    def shutdown(self) -> None:
        self._is_on = False

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():

            async def _notify_all():
                async with self._cond:
                    self._cond.notify_all()

            loop.create_task(_notify_all())

    def items(self) -> list[T]:
        return list(self._queue)
