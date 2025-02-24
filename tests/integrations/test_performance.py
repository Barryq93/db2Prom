import pytest
import time
from db2Prom.db2 import Db2Connection
from db2Prom.prometheus import CustomExporter

@pytest.fixture
def db2_connection():
    return Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass", exporter=CustomExporter())

@pytest.fixture
def prometheus_exporter():
    return CustomExporter(port=9877)

def test_query_execution_performance(db2_connection):
    """
    Test the performance of query execution.
    """
    query = "SELECT * FROM sysibm.sysdummy1"
    start_time = time.time()
    db2_connection.execute(query, "performance_test")
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Query execution time: {execution_time:.4f} seconds")
    assert execution_time < 1.0  # Ensure query executes within 1 second

def test_metric_export_performance(prometheus_exporter):
    """
    Test the performance of metric export.
    """
    prometheus_exporter.create_gauge("test_gauge", "Test gauge description")
    start_time = time.time()
    prometheus_exporter.set_gauge("test_gauge", 42)
    end_time = time.time()
    export_time = end_time - start_time
    print(f"Metric export time: {export_time:.4f} seconds")
    assert export_time < 0.1  # Ensure metric export completes within 100ms