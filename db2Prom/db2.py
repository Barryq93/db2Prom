#import os 
#os.add_dll_directory("D:\\Learning\\Code\\Python\\db2Prom\\.venv\\Lib\\site-packages\\clidriver\\bin")
import ibm_db
import logging
import asyncio
from typing import AsyncIterator

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

    async def execute(
        self,
        query: str,
        name: str,
        params: list | tuple | None = None,
        timeout: float | None = None,
        max_rows: int | None = None,
    ) -> AsyncIterator[list]:
        """
        Execute a SQL query and yield the results incrementally.
        The execution is offloaded to a thread using run_in_executor. If the
        execution exceeds the provided timeout, the running thread is cancelled
        and an error metric is emitted.
        """
        try:
            if not self.conn:
                return

            loop = asyncio.get_running_loop()
            queue: asyncio.Queue = asyncio.Queue()
            sentinel = object()
            errors: list[Exception] = []

            def run_query():
                stmt = None
                try:
                    stmt = ibm_db.prepare(self.conn, query)
                    if params is not None:
                        ibm_db.execute(stmt, params)
                    else:
                        ibm_db.execute(stmt)
                    row_count = 0
                    row = ibm_db.fetch_tuple(stmt)
                    while row:
                        loop.call_soon_threadsafe(queue.put_nowait, list(row))
                        row_count += 1
                        if max_rows is not None and row_count >= max_rows:
                            break
                        row = ibm_db.fetch_tuple(stmt)
                except Exception as exc:  # Capture exceptions from thread
                    errors.append(exc)
                finally:
                    if stmt is not None:
                        ibm_db.free_stmt(stmt)
                    loop.call_soon_threadsafe(queue.put_nowait, sentinel)

            future = loop.run_in_executor(None, run_query)

            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    future.cancel()
                    logger.warning(
                        f"[{self.connection_string_print}] [{name}] execution timed out"
                    )
                    self.exporter.set_gauge("db2_query_timeout", 1, {"query": name})
                    self.conn = None
                    raise
                if item is sentinel:
                    break
                yield item

            await future
            if errors:
                raise errors[0]

            logger.debug(f"[{self.connection_string_print}] [{name}] executed")
        except Exception as e:
            logger.warning(
                f"[{self.connection_string_print}] [{name}] failed to execute: {e}"
            )
            self.conn = None
            raise

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
