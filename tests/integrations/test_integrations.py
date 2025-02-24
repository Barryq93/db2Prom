import pytest
from db2Prom.db2 import Db2Connection
from db2Prom.prometheus import CustomExporter

@pytest.fixture
def db2_connection():
    return Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass")

@pytest.fixture
def prometheus_exporter():
    return CustomExporter(port=9877)

def test_db2_connection(db2_connection):
    """
    Test DB2 connection establishment.
    """
    db2_connection.connect()
    assert db2_connection.conn is not None

def test_prometheus_exporter(prometheus_exporter):
    """
    Test Prometheus exporter initialization.
    """
    prometheus_exporter.create_gauge("test_gauge", "Test gauge description")
    prometheus_exporter.set_gauge("test_gauge", 42)
    assert "db2_test_gauge" in prometheus_exporter.metric_dict