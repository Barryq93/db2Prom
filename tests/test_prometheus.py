import unittest
import unittest
import sys
import types
from unittest.mock import patch, MagicMock

# Stub prometheus_client so tests do not require the real dependency
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
    @patch('db2Prom.prometheus.socket.gethostname', return_value='test-host')
    def test_start_exporter_default_host(self, mock_gethostname, mock_start_http_server):
        """Exporter binds to the OS hostname by default."""
        exporter = CustomExporter()
        exporter.start()
        mock_start_http_server.assert_called_once_with(9877, addr="test-host")

    @patch('db2Prom.prometheus.start_http_server')
    def test_start_exporter_with_custom_host(self, mock_start_http_server):
        """Exporter binds to a specified host when provided."""
        exporter = CustomExporter(port=9877, host="127.0.0.1")
        exporter.start()
        mock_start_http_server.assert_called_once_with(9877, addr="127.0.0.1")

    def test_query_cache_initialisation_and_record(self):
        """Query names from config initialise cache and metrics."""
        exporter = CustomExporter(query_names=["q1"])
        exporter.create_gauge(
            "db2_query_duration_seconds",
            "Duration of DB2 query execution in seconds",
            ["query"],
        )
        exporter.create_gauge(
            "db2_query_last_success_timestamp",
            "Unix timestamp of the last successful DB2 query execution",
            ["query"],
        )
        exporter.set_gauge("db2_query_duration_seconds", 0.0, {"query": "q1"})
        exporter.set_gauge("db2_query_last_success_timestamp", 0.0, {"query": "q1"})
        # Cache starts at 0 for configured queries
        self.assertEqual(exporter.query_last_success["q1"], 0.0)
        exporter.record_query_duration("q1", 1.23)
        exporter.record_query_success("q1")
        self.assertGreater(exporter.query_last_success["q1"], 0)

if __name__ == '__main__':
    unittest.main()
