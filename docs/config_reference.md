# Configuration Reference

## Global Configuration
- `log_level`: Logging level (e.g., INFO, DEBUG).
- `retry_conn_interval`: Interval (in seconds) for retrying DB2 connections.
- `default_time_interval`: Default interval (in seconds) for query execution.
- `log_path`: Directory for storing log files.
- `port`: Port for the Prometheus metrics endpoint.

## Connections
- `db_host`: DB2 server hostname.
- `db_name`: Database name.
- `db_port`: Database port.
- `db_user`: Database username.
- `db_passwd`: Database password (encrypted).
- `tags`: Tags for the connection.
- `extra_labels`: Additional labels for metrics.

## Queries
- `name`: Name of the query.
- `query`: SQL query to execute.
- `time_interval`: Interval (in seconds) for executing the query.
- `gauges`: List of gauges to create from the query results.