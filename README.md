# db2Prom

> Dynamic Prometheus exporter for IBM Db2 in Python

db2Prom is a Python-based tool designed for exporting metrics from IBM Db2 databases to Prometheus. It builds upon the foundation of db2dexpo by arapozojr, enhancing functionality and flexibility for monitoring Db2 instances.

## Overview

db2Prom allows users to define their own SQL queries, execute them against one or more Db2 databases, and create Prometheus gauge metrics based on the results. This enables comprehensive monitoring at both the Db2 system level (e.g., buffer pool performance, hit ratio) and application-specific database metrics.

Key features include:

- **Customizable Queries**: Write SQL queries tailored to your monitoring needs.
- **Dynamic Labeling**: Define dynamic labels for metrics based on query results.
- **Asynchronous Execution**: Run multiple queries concurrently for optimal performance.
- **Persistent Connections**: Automatically reconnect to databases if the connection is dropped.
- **Configuration via YAML**: Easily configure which metrics to export and which databases to connect using YAML files.
- **Label Sanitization**: Clean DB-sourced label values so they contain only letters, numbers, and underscores. Any character outside `[A-Za-z0-9_]` (e.g., spaces, hyphens, slashes) is replaced with `_`, and values longer than 100 characters are trimmed.

# Changes from db2dexpo

## Enhanced Logging and Error Handling

- Improved logging messages throughout the application for better clarity and error reporting.
- Added comprehensive error handling mechanisms to gracefully manage exceptions and errors.

## Extended Metrics Export

- Expanded the metrics export functionality to include additional database performance metrics beyond standard connections.
- Introduced flexibility in defining and exporting metrics based on user-defined queries and configurations.

## Configuration Flexibility

- Enhanced configuration options via YAML files to provide more dynamic setup capabilities.
- Users can now easily define and customize database connections, queries, and metrics through configurable YAML files.

## Bug Fixes and Optimization

- Optimized codebase for improved performance and reliability.

## Documentation and Readme Updates

- Updated `README.md` to reflect changes, installation instructions, and usage guidelines specific to `db2Prom`.
- Added comprehensive examples and outputs to demonstrate usage scenarios, including Docker setup and metric visualization.

Grateful to [arapozojr](https://github.com/arapozojr) for their initial work on `db2dexpo`, which served as the foundation for this project.

## Running Locally

To run db2Prom locally, follow these steps:

### Prerequisites

- Python 3.10.8 or higher
- pip (Python package installer)

### Installation

Clone the repository:

```bash
git clone https://github.com/Barryq93/db2Prom.git
cd db2Prom
```

Install all required packages using pip:

```shell
pip3 install -r requirements.txt
```

Check [the example config YAML](config.example.yaml) on how to handle multiple databases with different access. Use this example YAML to also make your own config.yaml file, with your queries and gauge metrics.

Run the application:

```shell
python app.py config.yaml
```

The exporter listens on the port defined in `global_config` within
`config.yaml` and binds to the machine's hostname. Prometheus servers on other
machines can use that hostname to scrape the metrics endpoint.

Set DB2DEXPO_LOG_LEVEL to DEBUG to show query executions and metric updates.

Example output of application startup:

```text
2023-01-07 10:24:16,858 - db2dexpo.prometheus - INFO - [GAUGE] [db2_applications_count] created
2023-01-07 10:24:16,859 - db2dexpo.prometheus - INFO - [GAUGE] [db2_lockwaits_count] created
2023-01-07 10:24:16,859 - db2dexpo.prometheus - INFO - [GAUGE] [db2_lockwaits_maxwait_seconds] created
2023-01-07 10:24:16,859 - db2dexpo.prometheus - INFO - [GAUGE] [db2_employees_created] created
2023-01-07 10:24:16,860 - db2dexpo.prometheus - INFO - Db2DExpo server started at port 9877
2023-01-07 10:24:17,232 - db2dexpo.db2 - INFO - [127.0.0.1:50000/sample] connected
```

You can then open `http://<exporter-host>:9877/` and see the exported metrics.

Ctrl+c will stop the application.

## Running in Docker

Clone this repo:

```shell
git clone https://github.com/arapozojr/db2dexpo.git
cd db2dexpo/
```


Check [the example config YAML](config.example.yaml) on how to handle multiple databases with different access. Use this example YAML to also make your own config.yaml file, with your queries and gauge metrics.

Build Docker image:

```shell
docker build -t db2prompy .
```

Run a container:

```shell
docker run --name db2dexpo -it --env-file .env db2dexpo
```

See the exported metrics:

```shell
docker exec -it db2dexpo curl 127.0.0.1:9877
```

Example output:

```text
...
# HELP db2_applications_count Amount of applications connected and their states
# TYPE db2_applications_count gauge
db2_applications_count{appname="myapp",appstate="UOWWAIT",db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test"} 5.0
db2_applications_count{appname="myapp",appstate="UOWEXEC",db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test"} 2.0
db2_applications_count{appname="db2bp",appstate="UOWEXEC",db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test"} 1.0
# HELP db2_lockwaits_count Amount of lockwaits
# TYPE db2_lockwaits_count gauge
db2_lockwaits_count{db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test"} 0.0
# HELP db2_lockwaits_maxwait_seconds Maximum number of seconds apps are waiting to get lock
# TYPE db2_lockwaits_maxwait_seconds gauge
db2_lockwaits_maxwait_seconds{db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test"} 0.0
# HELP db2_employees_created Number of employees
# TYPE db2_employees_created gauge
db2_employees_created{db2instance="db2inst1",dbhost="127.0.0.1",dbname="sample",dbport="50000",dbenv="test",persontype="employee"} 1442.0
```

## Deployment considerations

The built-in HTTP server used by `db2Prom` binds to the machine's hostname and
does not provide transport security or authentication. For production
deployments, run the exporter behind a reverse proxy that handles TLS
termination and optional authentication middleware (e.g., basic auth) to
restrict access to the metrics endpoint.
