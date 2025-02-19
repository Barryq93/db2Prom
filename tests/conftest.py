import pytest
from db2Prom.db2 import Db2Connection
from db2Prom.prometheus import CustomExporter

@pytest.fixture
def db2_connection():
    return Db2Connection(db_name="test_db", db_hostname="localhost", db_port="50000", db_user="user", db_passwd="pass")

@pytest.fixture
def prometheus_exporter():
    return CustomExporter(port=9877)