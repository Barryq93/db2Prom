import unittest
from unittest.mock import patch, MagicMock
from db2Prom.db2 import Db2Connection

class TestDb2Connection(unittest.TestCase):

    @patch('ibm_db.pconnect')
    def test_connect_success(self, mock_pconnect):
        """
        Test that the DB2 connection is established successfully.
        """
        # Mock successful connection
        mock_pconnect.return_value = "mock_connection"

        # Mock the exporter
        mock_exporter = MagicMock()

        # Create Db2Connection instance
        db2_conn = Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass", exporter=mock_exporter)
        db2_conn.connect()

        # Verify the connection was established
        self.assertEqual(db2_conn.conn, "mock_connection")
        # Verify the connection status metric is set to 1 (reachable)
        mock_exporter.set_gauge.assert_called_with("db2_connection_status", 1)

    @patch('ibm_db.pconnect')
    def test_connect_failure(self, mock_pconnect):
        """
        Test that the DB2 connection handles failures correctly.
        """
        # Mock connection failure
        mock_pconnect.side_effect = Exception("Connection failed")

        # Mock the exporter
        mock_exporter = MagicMock()

        # Create Db2Connection instance
        db2_conn = Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass", exporter=mock_exporter)

        # Call the connect method and verify it raises an exception
        with self.assertRaises(Exception):
            db2_conn.connect()

        # Verify the connection is None
        self.assertIsNone(db2_conn.conn)
        # Verify the connection status metric is set to 0 (unreachable)
        mock_exporter.set_gauge.assert_called_with("db2_connection_status", 0)

    @patch('ibm_db.exec_immediate')
    @patch('ibm_db.fetch_tuple')
    def test_execute_query(self, mock_fetch_tuple, mock_exec_immediate):
        """
        Test that a SQL query is executed successfully.
        """
        # Mock query execution
        mock_exec_immediate.return_value = "mock_statement"
        mock_fetch_tuple.side_effect = [[1, "data"], None]  # Simulate one row of data

        # Mock the exporter
        mock_exporter = MagicMock()

        # Create Db2Connection instance
        db2_conn = Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass", exporter=mock_exporter)
        db2_conn.conn = "mock_connection"  # Simulate an active connection

        # Execute the query
        result = db2_conn.execute("SELECT * FROM table", "test_query")
        self.assertEqual(result, [[1, "data"]])

    @patch('ibm_db.close')
    def test_close_connection(self, mock_close):
        """
        Test that the DB2 connection is closed successfully.
        """
        # Mock the exporter
        mock_exporter = MagicMock()

        # Create Db2Connection instance
        db2_conn = Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass", exporter=mock_exporter)
        db2_conn.conn = "mock_connection"  # Simulate an active connection

        # Close the connection
        db2_conn.close()

        # Verify the connection is None
        self.assertIsNone(db2_conn.conn)

if __name__ == '__main__':
    unittest.main()