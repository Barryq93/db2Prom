import unittest
import asyncio
import time
import sys
import types
from unittest.mock import patch, MagicMock

# Provide a minimal mock for the ``ibm_db`` module so the tests can run
# without the actual dependency being installed.
ibm_db_mock = types.SimpleNamespace(
    SQL_ATTR_INFO_PROGRAMNAME=0,
    SQL_ATTR_INFO_WRKSTNNAME=0,
    SQL_ATTR_INFO_ACCTSTR=0,
    SQL_ATTR_INFO_APPLNAME=0,
    pconnect=MagicMock(),
    prepare=MagicMock(),
    execute=MagicMock(),
    fetch_tuple=MagicMock(),
    free_stmt=MagicMock(),
    close=MagicMock(),
)
sys.modules.setdefault("ibm_db", ibm_db_mock)

from db2Prom.db2 import Db2Connection
from db2Prom.prometheus import CustomExporter


class TestDb2Connection(unittest.TestCase):

    @patch('ibm_db.pconnect')
    def test_connect_success(self, mock_pconnect):
        """Test that the DB2 connection is established successfully."""
        mock_pconnect.return_value = "mock_connection"
        mock_exporter = MagicMock()
        db2_conn = Db2Connection(
            db_name="test_db",
            db_hostname="localhost",
            db_port="50000",
            db_user="user",
            db_passwd="pass",
            exporter=mock_exporter,
        )
        db2_conn.connect()
        self.assertEqual(db2_conn.conn, "mock_connection")
        mock_exporter.set_gauge.assert_called_with(
            "db2_connection_status",
            1,
            {"dbhost": "localhost", "dbname": "test_db"},
        )

    @patch('ibm_db.pconnect')
    def test_connect_failure(self, mock_pconnect):
        """Test that the DB2 connection handles failures correctly."""
        mock_pconnect.side_effect = Exception("Connection failed")
        mock_exporter = MagicMock()
        db2_conn = Db2Connection(
            db_name="test_db",
            db_hostname="localhost",
            db_port="50000",
            db_user="user",
            db_passwd="pass",
            exporter=mock_exporter,
        )
        with self.assertRaises(Exception):
            db2_conn.connect()
        self.assertIsNone(db2_conn.conn)
        mock_exporter.set_gauge.assert_called_with(
            "db2_connection_status",
            0,
            {"dbhost": "localhost", "dbname": "test_db"},
        )

    @patch('ibm_db.free_stmt')
    @patch('ibm_db.fetch_tuple')
    @patch('ibm_db.execute')
    @patch('ibm_db.prepare')
    def test_execute_query(self, mock_prepare, mock_execute, mock_fetch_tuple, mock_free_stmt):
        """Test that a SQL query is executed successfully."""
        mock_prepare.return_value = "mock_statement"
        mock_execute.return_value = True
        mock_fetch_tuple.side_effect = [[1, "data"], None]
        mock_exporter = MagicMock()
        db2_conn = Db2Connection(
            db_name="test_db",
            db_hostname="localhost",
            db_port="50000",
            db_user="user",
            db_passwd="pass",
            exporter=mock_exporter,
        )
        db2_conn.conn = "mock_connection"

        async def run():
            return [
                row
                async for row in db2_conn.execute(
                    "SELECT * FROM table WHERE id = ?",
                    "test_query",
                    params=[1],
                )
            ]

        result = asyncio.run(run())
        self.assertEqual(result, [[1, "data"]])
        mock_free_stmt.assert_called_once_with("mock_statement")

    @patch('ibm_db.free_stmt')
    @patch('ibm_db.fetch_tuple')
    @patch('ibm_db.execute')
    @patch('ibm_db.prepare')
    def test_execute_query_max_rows(self, mock_prepare, mock_execute, mock_fetch_tuple, mock_free_stmt):
        """Test that max_rows limits the number of returned rows."""
        mock_prepare.return_value = "mock_statement"
        mock_execute.return_value = True
        mock_fetch_tuple.side_effect = [[1, "data"], [2, "data2"], None]
        mock_exporter = MagicMock()
        db2_conn = Db2Connection(
            db_name="test_db",
            db_hostname="localhost",
            db_port="50000",
            db_user="user",
            db_passwd="pass",
            exporter=mock_exporter,
        )
        db2_conn.conn = "mock_connection"

        async def run():
            return [
                row
                async for row in db2_conn.execute(
                    "SELECT * FROM table", "test_query", max_rows=1
                )
            ]

        result = asyncio.run(run())
        self.assertEqual(result, [[1, "data"]])
        mock_free_stmt.assert_called_once_with("mock_statement")

    @patch('ibm_db.close')
    @patch('ibm_db.free_stmt')
    @patch('ibm_db.fetch_tuple')
    @patch('ibm_db.execute')
    @patch('ibm_db.prepare')
    def test_execute_query_exception_calls_free_stmt(self, mock_prepare, mock_execute, mock_fetch_tuple, mock_free_stmt, mock_close):
        """Ensure free_stmt and close are called when fetch raises an exception."""
        mock_prepare.return_value = "mock_statement"
        mock_execute.return_value = True
        mock_fetch_tuple.side_effect = Exception("fetch failed")
        mock_exporter = MagicMock()
        db2_conn = Db2Connection(
            db_name="test_db",
            db_hostname="localhost",
            db_port="50000",
            db_user="user",
            db_passwd="pass",
            exporter=mock_exporter,
        )
        db2_conn.conn = "mock_connection"

        async def run():
            async for _ in db2_conn.execute("SELECT * FROM table", "test_query"):
                pass

        with self.assertRaises(Exception):
            asyncio.run(run())
        mock_free_stmt.assert_called_once_with("mock_statement")
        mock_close.assert_called_once_with("mock_connection")
        self.assertIsNone(db2_conn.conn)

    @patch('ibm_db.prepare')
    @patch('ibm_db.execute')
    def test_execute_timeout(self, mock_execute, mock_prepare):
        """Test that a timeout emits an error metric and propagates."""
        def slow_exec(*args, **kwargs):
            time.sleep(0.05)
            return True
        mock_prepare.return_value = "mock_statement"
        mock_execute.side_effect = slow_exec
        exporter = CustomExporter()
        db2_conn = Db2Connection(
            db_name="test_db",
            db_hostname="localhost",
            db_port="50000",
            db_user="user",
            db_passwd="pass",
            exporter=exporter,
        )
        db2_conn.conn = "mock_connection"

        async def run():
            async for _ in db2_conn.execute(
                "SELECT * FROM table", "test_query", timeout=0.01
            ):
                pass

        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run(run())
        gauge_value = (
            exporter.metric_dict["db2_query_timeout"]
            .labels(query="test_query")
            ._value.get()
        )
        self.assertEqual(gauge_value, 1)
        self.assertIsNone(db2_conn.conn)

    def test_exporter_initializes_query_timeout_gauge(self):
        """Ensure exporter creates the db2_query_timeout gauge."""
        exporter = CustomExporter()
        self.assertIn("db2_query_timeout", exporter.metric_dict)
        gauge = exporter.metric_dict["db2_query_timeout"]
        self.assertIn("query", gauge._labelnames)

    @patch('ibm_db.close')
    @patch('ibm_db.prepare')
    def test_execute_exception_resets_connection(self, mock_prepare, mock_close):
        """Test that an execution exception closes and resets the connection."""
        mock_prepare.side_effect = Exception("prepare failed")
        mock_exporter = MagicMock()
        db2_conn = Db2Connection(
            db_name="test_db",
            db_hostname="localhost",
            db_port="50000",
            db_user="user",
            db_passwd="pass",
            exporter=mock_exporter,
        )
        db2_conn.conn = "mock_connection"

        async def run():
            async for _ in db2_conn.execute("SELECT 1", "test_query"):
                pass

        with self.assertRaises(Exception):
            asyncio.run(run())
        mock_close.assert_called_once_with("mock_connection")
        self.assertIsNone(db2_conn.conn)

    @patch('ibm_db.close')
    def test_close_connection(self, mock_close):
        """Test that the DB2 connection is closed successfully."""
        mock_exporter = MagicMock()
        db2_conn = Db2Connection(
            db_name="test_db",
            db_hostname="localhost",
            db_port="50000",
            db_user="user",
            db_passwd="pass",
            exporter=mock_exporter,
        )
        db2_conn.conn = "mock_connection"
        db2_conn.close()
        self.assertIsNone(db2_conn.conn)


if __name__ == '__main__':
    unittest.main()
