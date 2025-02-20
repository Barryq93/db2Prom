import os 
os.add_dll_directory("D:\\Learning\\Code\\Python\\db2Prom\\.venv\\Lib\\site-packages\\clidriver\\bin")
import ibm_db
import logging

logger = logging.getLogger(__name__)

APPLICATION_NAME = "DB2PROM"

class Db2Connection:
    def __init__(self, db_name: str, db_hostname: str, db_port: str, db_user: str, db_passwd: str, exporter):
        """
        Initialize DB2 connection with the provided configuration.
        """
        self.connection_string = "DATABASE={};HOSTNAME={};PORT={};PROTOCOL=TCPIP;UID={};PWD={};".format(
            db_name, db_hostname, db_port, db_user, db_passwd)
        self.connection_string_print = "{}:{}/{}".format(db_hostname, db_port, db_name)
        self.conn = None
        self.exporter = exporter  # Pass the exporter to emit metrics

    def connect(self):
        """
        Establish a connection to the DB2 database.
        """
        options = {
            ibm_db.SQL_ATTR_INFO_PROGRAMNAME: APPLICATION_NAME,
            ibm_db.SQL_ATTR_INFO_WRKSTNNAME: APPLICATION_NAME,
            ibm_db.SQL_ATTR_INFO_ACCTSTR: APPLICATION_NAME,
            ibm_db.SQL_ATTR_INFO_APPLNAME: APPLICATION_NAME
        }
        try:
            if not self.conn:
                conn = ibm_db.pconnect(self.connection_string, "", "", options)
                logger.info(f"[{self.connection_string_print}] connected")
                self.conn = conn
                # Emit metric indicating the database is reachable
                self.exporter.set_gauge("db2_connection_status", 1)
        except Exception as e:
            logger.error(f"[{self.connection_string_print}] {e}")
            self.conn = None
            # Emit metric indicating the database is unreachable
            self.exporter.set_gauge("db2_connection_status", 0)
            raise e

    def execute(self, query: str, name: str):
        """
        Execute a SQL query and return the results.
        """
        try:
            if not self.conn:
                return []
            result = ibm_db.exec_immediate(self.conn, query)
            logger.debug(f"[{self.connection_string_print}] [{name}] executed")
            rows = []
            row = list(ibm_db.fetch_tuple(result))
            while row:
                rows.append(row)
                row = ibm_db.fetch_tuple(result)
            return rows
        except Exception as e:
            logger.warning(f"[{self.connection_string_print}] [{name}] failed to execute: {e}")
            return [[]]

    def close(self):
        """
        Close the DB2 connection.
        """
        try:
            if self.conn:
                ibm_db.close(self.conn)
                self.conn = None
                logger.info(f"[{self.connection_string_print}] closed")
        except Exception as e:
            logger.error(f"[{self.connection_string_print}] failed to close connection: {e}")