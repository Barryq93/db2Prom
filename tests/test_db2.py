import unittest
from unittest.mock import patch, MagicMock
from db2Prom.db2 import Db2Connection

class TestDb2Connection(unittest.TestCase):

    @patch('ibm_db.pconnect')
    def test_connect_success(self, mock_pconnect):
        # Mock successful connection
        mock_pconnect.return_value = "mock_connection"
        db2_conn = Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass")
        db2_conn.connect()
        self.assertEqual(db2_conn.conn, "mock_connection")

    @patch('ibm_db.pconnect')
    def test_connect_failure(self, mock_pconnect):
        # Mock connection failure
        mock_pconnect.side_effect = Exception("Connection failed")
        db2_conn = Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass")
        db2_conn.connect()
        self.assertIsNone(db2_conn.conn)

    @patch('ibm_db.exec_immediate')
    @patch('ibm_db.fetch_tuple')
    def test_execute_query(self, mock_fetch_tuple, mock_exec_immediate):
        # Mock query execution
        mock_exec_immediate.return_value = "mock_statement"
        mock_fetch_tuple.side_effect = [[1, "data"], None]  # Simulate one row of data
        db2_conn = Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass")
        db2_conn.conn = "mock_connection"  # Simulate an active connection
        result = db2_conn.execute("SELECT * FROM table", "test_query")
        self.assertEqual(result, [[1, "data"]])

    @patch('ibm_db.close')
    def test_close_connection(self, mock_close):
        # Mock closing connection
        db2_conn = Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass")
        db2_conn.conn = "mock_connection"
        db2_conn.close()
        self.assertIsNone(db2_conn.conn)

if __name__ == '__main__':
    unittest.main()