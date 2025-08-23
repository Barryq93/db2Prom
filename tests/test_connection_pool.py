import asyncio
import unittest

from db2Prom.connection_pool import ConnectionPool


class DummyConn:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class TestConnectionPool(unittest.TestCase):
    def test_acquire_release_and_close(self):
        pool = ConnectionPool(lambda: DummyConn(), maxsize=2)

        async def runner():
            conn = await pool.acquire()
            self.assertIsInstance(conn, DummyConn)
            pool.release(conn)
            await pool.close()
            self.assertTrue(conn.closed)

        asyncio.run(runner())


if __name__ == "__main__":
    unittest.main()

