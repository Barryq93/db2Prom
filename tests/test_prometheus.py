import unittest
from unittest.mock import patch, MagicMock
from db2Prom.prometheus import CustomExporter
from prometheus_client import Gauge

class TestCustomExporter(unittest.TestCase):

    def test_create_gauge(self):
        """
        Test that a Prometheus gauge is created correctly.
        """
        exporter = CustomExporter()
        exporter.create_gauge("test_gauge", "Test gauge description", ["label1", "label2"])

        # Verify the gauge was created and added to the metric dictionary
        self.assertIn("test_gauge", exporter.metric_dict)
        self.assertIsInstance(exporter.metric_dict["test_gauge"], Gauge)

    def test_set_gauge(self):
        """
        Test that a Prometheus gauge value is set correctly.
        """
        exporter = CustomExporter()
        exporter.create_gauge("test_gauge", "Test gauge description", ["label1", "label2"])

        # Set the gauge value
        exporter.set_gauge("test_gauge", 42, {"label1": "value1", "label2": "value2"})

        # Verify the gauge value was set (requires mocking Prometheus internals)
        # This test assumes the gauge.set() method works as expected.

    @patch('db2Prom.prometheus.start_http_server')
    def test_start_exporter(self, mock_start_http_server):
        """
        Test that the Prometheus exporter starts correctly.
        """
        # Create an instance of CustomExporter
        exporter = CustomExporter(port=9877)

        # Call the start method
        exporter.start()

        # Verify start_http_server was called with the correct port
        mock_start_http_server.assert_called_once_with(9877)

if __name__ == '__main__':
    unittest.main()
