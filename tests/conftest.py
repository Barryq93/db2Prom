import sys
import types
import pytest

# Provide a lightweight ``ibm_db`` stub so tests can patch DB2 client
# functions without requiring the real dependency.
ibm_db = types.ModuleType("ibm_db")
ibm_db.SQL_ATTR_INFO_PROGRAMNAME = 0
ibm_db.SQL_ATTR_INFO_WRKSTNNAME = 1
ibm_db.SQL_ATTR_INFO_ACCTSTR = 2
ibm_db.SQL_ATTR_INFO_APPLNAME = 3

def _dummy(*args, **kwargs):  # pragma: no cover - simple placeholder
    return object()

ibm_db.pconnect = _dummy
ibm_db.exec_immediate = _dummy
ibm_db.fetch_tuple = lambda stmt: ()
ibm_db.close = lambda conn: True

sys.modules.setdefault("ibm_db", ibm_db)

from db2Prom.db2 import Db2Connection
from db2Prom.prometheus import CustomExporter


@pytest.fixture
def db2_connection():
    return Db2Connection(
        db_name="test_db",
        db_hostname="localhost",
        db_port="50000",
        db_user="user",
        db_passwd="pass",
    )


@pytest.fixture
def prometheus_exporter():
    return CustomExporter(port=9877)