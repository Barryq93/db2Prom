import unittest
import asyncio
import sys
import types
from unittest.mock import patch, MagicMock, mock_open, AsyncMock
import os
import logging

# Minimal stubs for external dependencies so tests run without optional packages
class _Gauge:
    def __init__(self, *args, **kwargs):
        pass

    def labels(self, **kwargs):
        return self

    def set(self, value):
        pass

prom_client_stub = types.SimpleNamespace(
    start_http_server=MagicMock(),
    Gauge=_Gauge,
    REGISTRY=types.SimpleNamespace(_names_to_collectors={}),
)
sys.modules.setdefault("prometheus_client", prom_client_stub)

ibm_db_stub = types.SimpleNamespace(
    SQL_ATTR_INFO_PROGRAMNAME=0,
    SQL_ATTR_INFO_WRKSTNNAME=0,
    SQL_ATTR_INFO_ACCTSTR=0,
    SQL_ATTR_INFO_APPLNAME=0,
    pconnect=MagicMock(),
    exec_immediate=MagicMock(),
    fetch_tuple=MagicMock(),
    close=MagicMock(),
)
sys.modules.setdefault("ibm_db", ibm_db_stub)

from app import (
    setup_logging,
    db2_instance_connection,
    load_config_yaml,
    sanitize_config,
    sanitize_label_value,
    query_set,
)
from db2Prom.db2 import Db2Connection

class TestApp(unittest.TestCase):

    @patch('os.makedirs')
    @patch('app.RotatingFileHandler')
    @patch('logging.getLogger')
    def test_setup_logging(self, mock_get_logger, mock_rotating_file_handler, mock_makedirs):
        """
        Test that logging is set up correctly.
        """
        # Mock the logger and file system operations
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Mock the RotatingFileHandler to avoid actual file creation
        mock_handler = MagicMock()
        mock_rotating_file_handler.return_value = mock_handler

        # Call the function
        setup_logging("/fake/log/path", "INFO")

        # Verify the directory was created
        mock_makedirs.assert_called_once_with("/fake/log/path", exist_ok=True)

        # Verify the RotatingFileHandler was called with the correct paths
        mock_rotating_file_handler.assert_any_call(
            "/fake/log/path/db2prom.log", maxBytes=10 * 1024 * 1024, backupCount=5
        )
        mock_rotating_file_handler.assert_any_call(
            "/fake/log/path/db2prom.err", maxBytes=10 * 1024 * 1024, backupCount=5
        )

        # Verify the handlers were added to the logger
        self.assertEqual(mock_logger.addHandler.call_count, 2)  # Main log handler and error log handler

    @patch('app.Db2Connection')
    def test_db2_instance_connection(self, mock_db2_connection):
        """
        Test that a DB2 connection is created with the correct parameters.
        """
        # Mock the Db2Connection class
        mock_db2_connection.return_value = MagicMock()

        # Mock the exporter
        mock_exporter = MagicMock()

        # Test data
        config_connection = {
            "db_name": "test_db",
            "db_host": "localhost",
            "db_port": "50000",
            "db_user": "user",
            "db_passwd": "pass"
        }

        # Call the function
        db2_instance_connection(config_connection, mock_exporter)

        # Verify Db2Connection was called with the correct arguments
        mock_db2_connection.assert_called_once_with(
            db_name="test_db",
            db_hostname="localhost",
            db_port="50000",
            db_user="user",
            db_passwd="pass",
            exporter=mock_exporter  # Pass the exporter
        )

    def test_load_config_yaml(self):
        """
        Test that the YAML configuration file is loaded correctly.
        """
        # Mock the YAML file content
        yaml_content = """
        global_config:
          log_level: INFO
          retry_conn_interval: 60
          default_time_interval: 15
          log_path: "logs/"
          port: 9844
        """

        # Mock the file open function
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            config = load_config_yaml("fake_config.yaml")

            # Verify the configuration was loaded correctly
            self.assertEqual(config["global_config"]["log_level"], "INFO")
            self.assertEqual(config["global_config"]["retry_conn_interval"], 60)
            self.assertEqual(config["global_config"]["default_time_interval"], 15)

    def test_sanitize_config(self):
        config = {
            "connections": [{"db_user": "u", "db_passwd": "secret"}],
            "global_config": {"password": "another"},
        }
        sanitized = sanitize_config(config)
        self.assertEqual(sanitized["connections"][0]["db_passwd"], "******")
        self.assertEqual(sanitized["global_config"]["password"], "******")
        # Original config should remain unchanged
        self.assertEqual(config["connections"][0]["db_passwd"], "secret")

    def test_sanitize_label_value(self):
        # Replaces illegal characters and trims long strings
        raw = "inv@lid label!!" + "x" * 200
        sanitized = sanitize_label_value(raw)
        self.assertTrue(sanitized.startswith("inv_lid_label__"))
        self.assertLessEqual(len(sanitized), 100)

        # None or unsanitizable values fall back to INVALID_LABEL_STR
        self.assertEqual(sanitize_label_value(None), "-")

    @patch('app.asyncio.sleep', side_effect=asyncio.CancelledError)
    def test_query_set_sanitizes_db_labels(self, _):
        exporter = MagicMock()
        pool = MagicMock()
        conn = MagicMock()
        conn.connect = MagicMock()
        conn.execute = AsyncMock(return_value=[(1, "bad label!!")])
        pool.acquire = AsyncMock(return_value=conn)
        pool.release = MagicMock()

        config_connection = {"db_host": "h", "db_port": "p", "db_name": "n"}
        config_query = {
            "name": "q",
            "query": "sql",
            "gauges": [{"name": "m", "col": 1, "extra_labels": {"lbl": "$2"}}],
        }

        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(query_set(config_connection, pool, config_query, exporter, 1))

        # One of the calls should contain the sanitized label from the query result
        self.assertGreaterEqual(exporter.set_gauge.call_count, 1)
        found = False
        for call in exporter.set_gauge.call_args_list:
            lbls = call.args[2]
            if "lbl" in lbls:
                self.assertEqual(lbls["lbl"], sanitize_label_value("bad label!!"))
                found = True
                break
        self.assertTrue(found)

    @patch('app.asyncio.sleep', side_effect=asyncio.CancelledError)
    def test_query_set_passes_max_rows(self, _):
        exporter = MagicMock()
        pool = MagicMock()
        conn = MagicMock()
        conn.connect = MagicMock()
        conn.execute = AsyncMock(return_value=[[1]])
        pool.acquire = AsyncMock(return_value=conn)
        pool.release = MagicMock()

        config_connection = {"db_host": "h", "db_port": "p", "db_name": "n"}
        config_query = {
            "name": "q",
            "query": "sql",
            "max_rows": 5,
            "gauges": [{"name": "m", "col": 1}],
        }

        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(query_set(config_connection, pool, config_query, exporter, 1))

        conn.execute.assert_awaited_with("sql", "q", timeout=None, max_rows=5)

if __name__ == '__main__':
    unittest.main()
