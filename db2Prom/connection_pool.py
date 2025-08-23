import asyncio


class ConnectionPool:
    """Simple asynchronous pool for :class:`Db2Connection` objects."""

    def __init__(self, factory, maxsize: int = 10):
        """
        Create a pool with ``maxsize`` connections produced by ``factory``.

        Parameters
        ----------
        factory:
            Callable returning a new ``Db2Connection`` instance.
        maxsize:
            Maximum number of connections to keep in the pool.
        """

        self._queue = asyncio.Queue(maxsize=maxsize)
        for _ in range(maxsize):
            # Connections are created lazily; ``connect`` will be called by
            # ``query_set`` before use.
            self._queue.put_nowait(factory())

    async def acquire(self):
        """Acquire a connection from the pool."""
        return await self._queue.get()

    def release(self, conn):
        """Return a connection to the pool."""
        self._queue.put_nowait(conn)

    async def close(self):
        """Close all connections currently in the pool."""
        while not self._queue.empty():
            conn = await self._queue.get()
            try:
                conn.close()
            finally:
                # Ensure the connection isn't reused after closing
                pass

