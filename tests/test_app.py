import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import logging
from app import setup_logging, db2_instance_connection, load_config_yaml, validate_config
from db2Prom.db2 import Db2Connection

class TestApp(unittest.TestCase):

    @patch('os.makedirs')
    @patch('logging.handlers.RotatingFileHandler')
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
        self.assertEqual(mock_logger.addHandler.call_count, 3)  # Main log handler, error log handler, and console handler

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

    def test_validate_config(self):
        """
        Test that the configuration validation works correctly.
        """
        valid_config = {
            "global_config": {
                "log_level": "INFO",
                "retry_conn_interval": 60,
                "default_time_interval": 15,
                "log_path": "logs/",
                "port": 9844
            },
            "connections": [
                {
                    "db_host": "localhost",
                    "db_name": "test_db",
                    "db_port": "50000",
                    "db_user": "user",
                    "db_passwd": "pass"
                }
            ],
            "queries": [
                {
                    "name": "test_query",
                    "query": "SELECT 1",
                    "gauges": [
                        {
                            "name": "test_gauge",
                            "desc": "Test gauge",
                            "col": 1
                        }
                    ]
                }
            ]
        }

        # Test valid config
        try:
            validate_config(valid_config)
        except ValueError as ve:
            self.fail(f"validate_config raised ValueError unexpectedly: {ve}")

        # Test invalid config (missing global_config)
        invalid_config = valid_config.copy()
        del invalid_config["global_config"]
        with self.assertRaises(ValueError):
            validate_config(invalid_config)

if __name__ == '__main__':
    unittest.main()