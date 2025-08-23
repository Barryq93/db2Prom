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
    exec_immediate=MagicMock(),
    fetch_tuple=MagicMock(),
    close=MagicMock(),
)
sys.modules.setdefault("ibm_db", ibm_db_mock)

from db2Prom.db2 import Db2Connection


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
        mock_exporter.set_gauge.assert_called_with("db2_connection_status", 1)

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
        mock_exporter.set_gauge.assert_called_with("db2_connection_status", 0)

    @patch('ibm_db.exec_immediate')
    @patch('ibm_db.fetch_tuple')
    def test_execute_query(self, mock_fetch_tuple, mock_exec_immediate):
        """Test that a SQL query is executed successfully."""
        mock_exec_immediate.return_value = "mock_statement"
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
        result = asyncio.run(db2_conn.execute("SELECT * FROM table", "test_query"))
        self.assertEqual(result, [[1, "data"]])

    @patch('ibm_db.exec_immediate')
    @patch('ibm_db.fetch_tuple')
    def test_execute_query_max_rows(self, mock_fetch_tuple, mock_exec_immediate):
        """Test that max_rows limits the number of returned rows."""
        mock_exec_immediate.return_value = "mock_statement"
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
        result = asyncio.run(
            db2_conn.execute("SELECT * FROM table", "test_query", max_rows=1)
        )
        self.assertEqual(result, [[1, "data"]])

    @patch('ibm_db.exec_immediate')
    def test_execute_timeout(self, mock_exec_immediate):
        """Test that a timeout emits an error metric and returns an empty result."""
        def slow_exec(*args, **kwargs):
            time.sleep(0.05)
            return "mock_statement"
        mock_exec_immediate.side_effect = slow_exec
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
        result = asyncio.run(
            db2_conn.execute("SELECT * FROM table", "test_query", timeout=0.01)
        )
        self.assertEqual(result, [[]])
        mock_exporter.set_gauge.assert_called_with(
            "db2_query_timeout", 1, {"query": "test_query"}
        )

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
