# -*- coding: utf-8 -*-

import os
import sys
import signal
import argparse
import yaml
import logging
import asyncio
import re
import copy
import random
import time
from logging.handlers import RotatingFileHandler
from db2Prom.db2 import Db2Connection
from db2Prom.prometheus import CustomExporter, INVALID_LABEL_STR
from db2Prom.connection_pool import ConnectionPool

# Maximum length for a Prometheus label value
MAX_LABEL_LENGTH = 100

# Precompiled regex to replace illegal characters in label values
_LABEL_CLEAN_RE = re.compile(r"[^a-zA-Z0-9_]")


def sanitize_label_value(value, max_length: int = MAX_LABEL_LENGTH) -> str:
    """Sanitize a label value for Prometheus metrics.

    Parameters
    ----------
    value : Any
        The value to sanitize. If ``None`` or cannot be converted to a string,
        ``INVALID_LABEL_STR`` is returned.
    max_length : int, optional
        Maximum length of the resulting string. Longer values are trimmed.

    Returns
    -------
    str
        A sanitized label value containing only alphanumeric characters and
        underscores, truncated to ``max_length``. If the value cannot be
        sanitized, ``INVALID_LABEL_STR`` is returned.
    """

    if value is None:
        return INVALID_LABEL_STR

    try:
        value_str = str(value)
    except Exception:
        return INVALID_LABEL_STR

    sanitized = _LABEL_CLEAN_RE.sub("_", value_str)
    if not sanitized:
        return INVALID_LABEL_STR

    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    return sanitized

def setup_logging(log_path, log_level, log_console=True):
    """
    Set up logging with rotating file handlers and optional console output.
    """
    # Create log directory if it doesn't exist
    os.makedirs(log_path, exist_ok=True)

    # Configure logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Main log handler (rotating file handler)
    log_file = os.path.join(log_path, "db2prom.log")
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Error log handler (rotating file handler)
    error_log_file = os.path.join(log_path, "db2prom.err")
    error_handler = RotatingFileHandler(error_log_file, maxBytes=10*1024*1024, backupCount=5)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # Optional console handler
    if log_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

def db2_instance_connection(config_connection, exporter):
    """
    Establishes a DB2 connection using provided configuration.
    """
    logging.info("Setting up DB2 connection with provided configuration.")
    conn = {
        "db_name": config_connection["db_name"],
        "db_hostname": config_connection["db_host"],
        "db_port": config_connection["db_port"],
        "db_user": config_connection["db_user"],
        "db_passwd": config_connection["db_passwd"],
        "exporter": exporter  # Pass the exporter to Db2Connection for emitting metrics
    }

    # Validate connection parameters
    for key, value in conn.items():
        if not value and key != "exporter":  # Exclude exporter from validation
            logging.fatal(f"Missing {key} field for connection.")
            sys.exit(1)

    return Db2Connection(**conn)

async def query_set(config_connection, pool, config_query, exporter, default_time_interval):
    """
    Asynchronous function to execute queries and export metrics.
    """
    logging.info(
        f"Starting query set for: {config_query['name']} with interval {config_query.get('time_interval', default_time_interval)} seconds."
    )
    time_interval = config_query.get("time_interval", default_time_interval)
    # Base delay between successful runs; also serves as the starting point for retries
    retry_delay = time_interval
    # Cap for exponential backoff to prevent unbounded growth
    max_retry_delay = config_query.get("max_retry_delay", 300)
    query_label = sanitize_label_value(config_query["name"])

    while True:
        conn = await pool.acquire()
        success = True
        start_time = None
        try:
            # Ensure DB2 connection is established before each query execution
            conn.connect()

            # Prepare labels for custom metrics
            c_labels = {
                "dbhost": config_connection["db_host"],
                "dbport": config_connection["db_port"],
                "dbname": config_connection["db_name"],
            }
            if "extra_labels" in config_connection:
                c_labels.update(config_connection["extra_labels"])

            max_conn_labels = {"dbhost", "dbenv", "dbname", "dbinstance", "dbport"}
            c_labels = {i: INVALID_LABEL_STR for i in max_conn_labels} | c_labels

            # Execute query and export metrics
            start_time = time.perf_counter()
            res = [
                row
                async for row in conn.execute(
                    config_query["query"],
                    config_query["name"],
                    config_query.get("params"),
                    timeout=config_query.get("timeout"),
                    max_rows=config_query.get("max_rows"),
                )
            ]
            duration = time.perf_counter() - start_time
            exporter.record_query_duration(query_label, duration)
            g_counter = 0
            for g in config_query["gauges"]:
                if "extra_labels" in g:
                    g_labels = g["extra_labels"]
                else:
                    g_labels = {}

                if "col" in g:
                    col = int(g["col"]) - 1
                else:
                    col = g_counter

                has_special_labels = any(re.match(r'^\$\d+$', v) for v in g_labels.values())

                if not has_special_labels:
                    if res:
                        row = res[0]
                        labels_g = g_labels | c_labels
                        if row and len(row) >= col:
                            exporter.set_gauge(g["name"], row[col], labels_g)
                else:
                    for row in res:
                        g_labels_aux = g_labels.copy()
                        for k, v in g_labels_aux.items():
                            g_label_index = (
                                int(re.match(r'^\$(\d+)$', v).group(1)) - 1
                                if re.match(r'^\$(\d+)$', v)
                                else 0
                            )
                            raw_value = (
                                row[g_label_index]
                                if row and len(row) > g_label_index
                                else None
                            )
                            g_labels_aux[k] = sanitize_label_value(raw_value)
                        labels_g = g_labels_aux | c_labels
                        if row and len(row) >= col:
                            exporter.set_gauge(g["name"], row[col], labels_g)
                g_counter += 1
            exporter.record_query_success(query_label)
        except Exception as e:
            if start_time is not None:
                duration = time.perf_counter() - start_time
                exporter.record_query_duration(query_label, duration)
            success = False
            logging.error(f"Error executing query {config_query['name']}: {e}")
        finally:
            pool.release(conn)
            if success:
                # Reset delay after a successful execution so the normal interval resumes
                retry_delay = time_interval
                await asyncio.sleep(time_interval)
            else:
                # Exponentially increase delay, capped at max_retry_delay, and add jitter
                retry_delay = min(retry_delay * 2, max_retry_delay)
                jitter = random.uniform(0, retry_delay * 0.1)  # up to 10% jitter to avoid lockstep
                await asyncio.sleep(retry_delay + jitter)

def load_config_yaml(file_str):
    """
    Loads and parses a YAML configuration file.
    """
    logging.info(f"Loading configuration file: {file_str}")
    try:
        with open(file_str, "r") as f:
            file_dict = yaml.safe_load(f)
            if not isinstance(file_dict, dict):
                logging.fatal(f"Could not parse '{file_str}' as dict")
                sys.exit(1)
            return file_dict
    except yaml.YAMLError as e:
        logging.fatal(f"File {file_str} is not a valid YAML: {e}")
        sys.exit(1)
    except FileNotFoundError:
        logging.fatal(f"File {file_str} not found")
        sys.exit(1)
    except Exception as e:
        logging.fatal(f"Could not open file {file_str}: {e}")
        sys.exit(1)

def sanitize_config(config):
    """
    Return a deep copy of the configuration with password fields masked.
    """
    def mask(item):
        if isinstance(item, dict):
            return {k: ('******' if 'pass' in k.lower() else mask(v)) for k, v in item.items()}
        if isinstance(item, list):
            return [mask(i) for i in item]
        return item

    return mask(copy.deepcopy(config))

def get_labels_list(config_connections):
    """
    Extracts a set of all unique connection labels.
    """
    max_conn_labels = set()
    for c in config_connections:
        if "extra_labels" in c:
            c_labels = c["extra_labels"]
        else:
            c_labels = {}
        max_conn_labels |= set(c_labels)
    max_conn_labels.add("dbhost")
    max_conn_labels.add("dbport")
    max_conn_labels.add("dbname")
    return max_conn_labels

def start_prometheus_exporter(config_queries, max_conn_labels, port):
    """Start the Prometheus exporter and initialize metrics."""
    logging.info(
        f"Starting Prometheus exporter on port {port} and initializing metrics."
    )
    try:
        # Only the query name is required for default query metrics to keep
        # label cardinality and memory usage low.
        query_names = [sanitize_label_value(q["name"]) for q in config_queries]
        custom_exporter = CustomExporter(port=port, query_names=query_names)

        # Default per-query metrics are configured from the YAML file so that
        # only queries defined there are exposed.
        custom_exporter.create_gauge(
            "db2_query_duration_seconds",
            "Duration of DB2 query execution in seconds",
            ["query"],
        )
        custom_exporter.create_gauge(
            "db2_query_last_success_timestamp",
            "Unix timestamp of the last successful DB2 query execution",
            ["query"],
        )
        for q in query_names:
            labels = {"query": q}
            custom_exporter.set_gauge("db2_query_duration_seconds", 0.0, labels)
            custom_exporter.set_gauge("db2_query_last_success_timestamp", 0.0, labels)
        for q in config_queries:
            if "gauges" not in q:
                raise Exception(f"{q} is missing 'gauges' key")
            for g in q["gauges"]:
                labels = g.get("extra_labels", {}).keys()
                labels = list(max_conn_labels | set(labels))
                name = g.get("name")
                if not name:
                    raise Exception("Some gauge metrics are missing name")
                desc = g.get("desc", "")
                custom_exporter.create_gauge(name, desc, labels)
        custom_exporter.start()
        return custom_exporter
    except Exception as e:
        logging.fatal(f"Could not start/init Prometheus Exporter server: {e}")
        raise e

async def main(config_connection, config_queries, exporter, default_time_interval, port):
    """Coordinate query execution using a connection pool."""
    executions = []
    pool = ConnectionPool(lambda: db2_instance_connection(config_connection, exporter), maxsize=10)
    try:
        tags = set(config_connection.get("tags", []))
        for q in config_queries:
            runs_on = set(q.get("runs_on", []))
            if runs_on and tags.isdisjoint(runs_on):
                continue
            if "query" not in q:
                raise Exception(f"{q} is missing 'query' key")
            executions.append(
                query_set(config_connection, pool, q, exporter, default_time_interval)
            )

        await asyncio.gather(*executions)
    except asyncio.CancelledError:
        logging.info("Connection task cancelled, shutting down.")
        raise
    finally:
        await pool.close()


async def run_all(config_connections, config_queries, exporter, default_time_interval, port):
    """Run query executors for all connections and handle termination signals."""
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _signal_handler():
        logging.info("Received termination signal, shutting down gracefully.")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    tasks = [
        asyncio.create_task(
            main(
                config_connection,
                config_queries,
                exporter,
                default_time_interval,
                port,
            )
        )
        for config_connection in config_connections
    ]

    await stop_event.wait()

    for t in tasks:
        t.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == '__main__':
    # Command-line argument parsing and main execution flow
    parser = argparse.ArgumentParser(description='DB2 Prometheus Exporter')
    parser.add_argument('config_file', type=str, help='Path to the config YAML file')
    args = parser.parse_args()

    if not args.config_file:
        logging.error("Error: Configuration file argument is missing.")
        sys.exit(1)

    try:
        # Load global configuration from YAML file
        config = load_config_yaml(args.config_file)
        logging.info(f"Loaded config: {sanitize_config(config)}")  # Logging loaded config
        
        global_config = config["global_config"]
        log_level = logging.getLevelName(global_config.get("log_level", "INFO"))
        log_path = global_config.get("log_path", "/path/to/logs/")
        port = global_config.get("port", 9844)
        log_console = global_config.get("log_console", True)

        # Setup logging configuration
        setup_logging(log_path, log_level, log_console)
        logging.info("Configuration file loaded successfully.")

        # Validate global configuration variables
        if int(global_config.get("default_time_interval", 15)) < 1:
            logging.fatal("Invalid value for default_time_interval")
            sys.exit(2)
        
        # Load YAML files for DB2 connections and queries
        config_connections = config["connections"]
        config_queries = config["queries"]
        
        # Get set of all connection labels
        max_conn_labels = get_labels_list(config_connections)
        logging.info(f"Max connection labels: {max_conn_labels}")  # Logging max connection labels
        
        # Start Prometheus exporter and initialize metrics
        exporter = start_prometheus_exporter(config_queries, max_conn_labels, port)

        # Run all tasks with asyncio.run for automatic loop management
        asyncio.run(
            run_all(
                config_connections,
                config_queries,
                exporter,
                int(global_config["default_time_interval"]),
                port,
            )
        )
    except KeyError as ke:
        logging.critical(f"{ke.args[0]} not found in global_config. Check configuration.")
        sys.exit(1)
    except Exception as e:
        logging.critical(f"Error loading configuration: {e}. Check configuration.")
        sys.exit(1)
