import os
import sys
import signal
import argparse
import yaml
import logging
import asyncio
import re
from logging.handlers import RotatingFileHandler
from db2Prom.db2 import Db2Connection  # Assuming Db2Connection is defined in db2Prom.db2
from db2Prom.prometheus import CustomExporter, INVALID_LABEL_STR  # Assuming these are defined in db2Prom.prometheus

def setup_logging(log_path, error_log_path, log_level):
    # Create log directory if it doesn't exist
    os.makedirs(log_path, exist_ok=True)
    os.makedirs(os.path.dirname(error_log_path), exist_ok=True)

    # Configure logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Main log handler (rotating file handler)
    log_file = os.path.join(log_path, "db2promservice.log")
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Error log handler (separate file)
    error_handler = logging.FileHandler(error_log_path)
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    error_handler.setFormatter(error_formatter)
    logger.addHandler(error_handler)

def db2_instance_connection(config_connection: dict):
    # Establishes a DB2 connection using provided configuration
    logging.info("Setting up DB2 connection with provided configuration.")
    conn = {
        "db_name": config_connection["db_name"],
        "db_hostname": config_connection["db_host"],
        "db_port": config_connection["db_port"],
        "db_user": config_connection["db_user"],
        "db_passwd": config_connection["db_passwd"]
    }

    # Validate connection parameters
    for key, value in conn.items():
        if not value:
            logging.fatal(f"Missing {key} field for connection.")
            sys.exit(1)

    return Db2Connection(**conn)

async def db2_keep_connection(db2_conn: Db2Connection, retry_time: int = 60):
    """
    Asynchronous function to maintain DB2 connection.
    
    Periodically attempts to keep the DB2 connection alive by reconnecting 
    at specified intervals (retry_time seconds).
    """
    logging.info(f"Starting DB2 connection keeper with retry interval {retry_time} seconds.")
    while True:
        try:
            db2_conn.connect()
        except Exception as e:
            logging.error(f"Error keeping DB2 connection: {e}")
        await asyncio.sleep(retry_time)

async def query_set(config_connection: dict, db2_conn: Db2Connection, config_query: dict, exporter: CustomExporter, default_time_interval: int):
    """
    Asynchronous function to execute queries and export metrics.
    
    Executes a set of queries defined in config_query at specified intervals 
    (default_time_interval seconds). Ensures DB2 connection is re-established 
    before each query execution and exports metrics using the provided exporter.
    """
    logging.info(f"Starting query set for: {config_query['name']} with interval {config_query.get('time_interval', default_time_interval)} seconds.")
    time_interval = config_query.get("time_interval", default_time_interval)

    while True:
        try:
            # Ensure DB2 connection is established before each query execution
            db2_conn.close()
            db2_conn.connect()

            # Prepare labels for metrics
            c_labels = {
                "dbhost": config_connection["db_host"],
                "dbport": config_connection["db_port"],
                "dbname": config_connection["db_name"],
            }
            if "extra_labels" in config_connection:
                c_labels = c_labels | config_connection["extra_labels"]
            c_labels = {i: INVALID_LABEL_STR for i in list(max_conn_labels)} | c_labels

            # Execute query and export metrics
            res = db2_conn.execute(config_query["query"], config_query["name"])
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
                        labels = g_labels | c_labels
                        if row and len(row) >= col:
                            exporter.set_gauge(g["name"], row[col], labels)
                else:
                    for row in res:
                        g_labels_aux = g_labels.copy()
                        for k, v in g_labels_aux.items():
                            g_label_index = int(re.match('^\$(\d+)$', v).group(1)) - 1 if re.match('^\$(\d+)$', v) else 0
                            g_labels_aux[k] = row[g_label_index] if row and len(row) >= g_label_index else INVALID_LABEL_STR
                        labels = g_labels_aux | c_labels
                        if row and len(row) >= col:
                            exporter.set_gauge(g["name"], row[col], labels)
                g_counter += 1
        except Exception as e:
            logging.error(f"Error executing query {config_query['name']}: {e}")
        finally:
            await asyncio.sleep(time_interval)

#########################################
# Load YAML config files
#########################################

def load_config_yaml(file_str: str):
    # Loads and parses a YAML configuration file
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

#########################################
# Get set of all connection labels
#########################################

def get_labels_list(config_connections: dict):
    # Extracts a set of all unique connection labels
    max_conn_labels = set()
    for c in config_connections:
        if "extra_labels" in c:
            c_labels = c["extra_labels"]
        else:
            c_labels = set()
        max_conn_labels |= set(c_labels)
    max_conn_labels.add("dbhost")
    max_conn_labels.add("dbport")
    max_conn_labels.add("dbname")
    return max_conn_labels

#########################################
# Start Prometheus Exporter
# and initialize metrics
#########################################

def start_prometheus_exporter(config_queries: dict, max_conn_labels: list, port: int):
    # Starts the Prometheus exporter and initializes metrics
    logging.info(f"Starting Prometheus exporter on port {port} and initializing metrics.")
    try:
        custom_exporter = CustomExporter(port=port)
        for q in config_queries:
            if "gauges" not in q:
                raise Exception(f"{q} is missing 'gauges' key")
            for g in q["gauges"]:
                labels = g["extra_labels"].keys() if "extra_labels" in g else []
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

#########################################
# Main function to coordinate tasks
#########################################

async def main(config_connection: dict, config_queries: dict, exporter: CustomExporter, default_time_interval: int, port: int):
    # Main function to coordinate DB2 connection keep-alive and query execution
    executions = []
    try:
        db2_conn = db2_instance_connection(config_connection)
        retry_connect_interval = config_connection["retry_conn_interval"]
        executions.append(db2_keep_connection(db2_conn, retry_connect_interval))

        for q in config_queries:
            if "query" not in q:
                raise Exception(f"{q} is missing 'query' key")
            executions.append(query_set(config_connection, db2_conn, q, exporter, default_time_interval))

        await asyncio.gather(*executions)
    except KeyboardInterrupt:
        logging.info("Received KeyboardInterrupt, shutting down.")
        return None

def signal_handler(sig, frame):
    # Handles termination signals (e.g., Ctrl+C) gracefully
    logging.info("Received termination signal, shutting down gracefully.")
    loop.stop()
    sys.exit(0)

if __name__ == '__main__':
    # Command-line argument parsing and main execution flow
    parser = argparse.ArgumentParser(description='DB2 Prometheus Exporter')
    parser.add_argument('config_file', type=str, help='Path to the config YAML file')
    args = parser.parse_args()

    if not args.config_file:
        print("Error: Configuration file argument is missing.")
        sys.exit(1)

    try:
        # Load global configuration from YAML file
        global_config = load_config_yaml(args.config_file)["global_config"]
        log_level = logging.getLevelName(global_config.get("log_level", "INFO"))
        log_path = global_config.get("log_path", "/path/to/logs/")
        error_log_path = global_config.get("error_log_path", "/path/to/error_logs/")
        port = global_config.get("port", 9844)

        # Setup logging configuration
        setup_logging(log_path, error_log_path, log_level)
        logging.info("Configuration file loaded successfully.")

        # Validate global configuration variables
        for current_variable in ["retry_conn_interval", "default_time_interval"]:
            if int(global_config.get(current_variable, 15)) < 1:
                logging.fatal(f"Invalid value for {current_variable}")
                sys.exit(2)

        # Load YAML files for DB2 connections and queries
        config_connections = load_config_yaml(global_config["config_connections"])
        config_queries = load_config_yaml(global_config["config_queries"])

        # Get set of all connection labels
        max_conn_labels = get_labels_list(config_connections)

        # Start Prometheus exporter and initialize metrics
        exporter = start_prometheus_exporter(config_queries, max_conn_labels, port)

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)

        # Start asyncio event loop and run main tasks
        try:
            loop = asyncio.get_event_loop()
            tasks = []
            for config_connection in config_connections:
                tasks.append(main(config_connection, config_queries, exporter, int(global_config["default_time_interval"]), port))
            loop.run_until_complete(asyncio.gather(*tasks))
        except KeyboardInterrupt:
            logging.info("Received KeyboardInterrupt, shutting down.")
    except Exception as e:
        logging.fatal(f"Fatal error: {e}")
        sys.exit(1)
