import ibm_db_dbi as dbi
import logging

logger = logging.getLogger(__name__)

class Db2Connection:
    def __init__(self, db_name: str, db_hostname: str, db_port: str, db_user: str, db_passwd: str, exporter):
        """
        Initialize DB2 connection with the provided configuration.
        """
        self.connection_string = f"DATABASE={db_name};HOSTNAME={db_hostname};PORT={db_port};PROTOCOL=TCPIP;UID={db_user};PWD={db_passwd};"
        self.connection_string_print = f"{db_hostname}:{db_port}/{db_name}"
        self.conn = None
        self.exporter = exporter  # Pass the exporter to emit metrics

    def connect(self):
        """
        Establish a connection to the DB2 database.
        """
        try:
            if not self.conn:
                self.conn = dbi.connect(self.connection_string)
                logger.info(f"[{self.connection_string_print}] connected")
                self.exporter.set_gauge("db2_connection_status", 1)
        except Exception as e:
            logger.error(f"[{self.connection_string_print}] {e}")
            self.conn = None
            self.exporter.set_gauge("db2_connection_status", 0)
            raise e

    def execute(self, query: str, name: str):
        """
        Execute a SQL query and return the results.
        """
        try:
            if not self.conn:
                return []
            result = self.conn.cursor().execute(query)
            logger.debug(f"[{self.connection_string_print}] [{name}] executed")
            rows = result.fetchall()
            return rows
        except Exception as e:
            logger.warning(f"[{self.connection_string_print}] [{name}] failed to execute: {e}")
            return []

    def close(self):
        """
        Close the DB2 connection.
        """
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
                logger.info(f"[{self.connection_string_print}] closed")
        except Exception as e:
            logger.error(f"[{self.connection_string_print}] failed to close connection: {e}")