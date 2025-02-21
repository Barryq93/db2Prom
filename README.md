---

# db2Prom

> Dynamic Prometheus exporter for IBM Db2 in Python

`db2Prom` is a Python-based tool designed for exporting metrics from IBM Db2 databases to Prometheus. It builds upon the foundation of [`db2dexpo`](https://github.com/arapozojr/db2dexpo) by [arapozojr](https://github.com/arapozojr), enhancing functionality and flexibility for monitoring Db2 instances.

---

## Table of Contents
1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Changes from db2dexpo](#changes-from-db2dexpo)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running Locally](#running-locally)
7. [Running in Docker](#running-in-docker)
8. [Building an Executable with PyInstaller](#building-an-executable-with-pyinstaller)
9. [Testing](#testing)
10. [Contributing](#contributing)
11. [License](#license)
12. [Acknowledgments](#acknowledgments)

---

## Overview

`db2Prom` allows users to define their own SQL queries, execute them against one or more Db2 databases, and create Prometheus gauge metrics based on the results. This enables comprehensive monitoring at both the Db2 system level (e.g., buffer pool performance, hit ratio) and application-specific database metrics.

---

## Key Features

- **Customizable Queries**: Write SQL queries tailored to your monitoring needs.
- **Dynamic Labeling**: Define dynamic labels for metrics based on query results.
- **Asynchronous Execution**: Run multiple queries concurrently for optimal performance.
- **Persistent Connections**: Automatically reconnect to databases if the connection is dropped.
- **Configuration via YAML**: Easily configure which metrics to export and which databases to connect using YAML files.
- **Enhanced Logging**: Improved logging messages for better clarity and error reporting.
- **Comprehensive Error Handling**: Gracefully manage exceptions and errors.

---

## Changes from db2dexpo

`db2Prom` builds upon the original `db2dexpo` project by [arapozojr](https://github.com/arapozojr) with the following enhancements:

- **Extended Metrics Export**: Added support for additional database performance metrics beyond standard connections.
- **Configuration Flexibility**: Enhanced configuration options via YAML files for dynamic setup capabilities.
- **Bug Fixes and Optimization**: Improved performance and reliability.
- **Documentation Updates**: Updated `README.md` with detailed installation instructions, usage guidelines, and examples.

---

## Installation

### Prerequisites
- Python 3.10.8 or higher.
- `pip` (Python package installer).
- IBM Db2 client libraries.

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/Barryq93/db2Prom.git
   cd db2Prom
   ```

2. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Install IBM Db2 client libraries:
   - Follow the [IBM Db2 documentation](https://www.ibm.com/docs/en/db2/11.5?topic=clients-db2-client) to set up the Db2 client.

---

## Configuration

The application is configured using a `config.yaml` file. Here’s an example configuration:

```yaml
global_config:
  log_level: INFO
  retry_conn_interval: 60
  default_time_interval: 15
  log_path: "logs/"
  port: 9877

queries:
  - name: "applications_count"
    runs_on: ["production"]
    time_interval: 10
    query: |
      SELECT COUNT(*) FROM sysibmadm.applications
    gauges:
      - name: "db2_applications_count"
        desc: "Amount of applications connected and their states"
        col: 1

connections:
  - db_host: "127.0.0.1"
    db_name: "sample"
    db_port: 50000
    db_user: "db2inst1"
    db_passwd: "password"
    tags: [production, proddb1]
    extra_labels:
      dbinstance: db2inst1
      dbenv: production
```

### Configuration Fields
- **`global_config`**:
  - `log_level`: Logging level (e.g., INFO, DEBUG).
  - `retry_conn_interval`: Interval (in seconds) to retry Db2 connection.
  - `default_time_interval`: Default interval (in seconds) for query execution.
  - `log_path`: Directory to store log files.
  - `port`: Port for the Prometheus HTTP server.

- **`queries`**:
  - `name`: Name of the query.
  - `query`: SQL query to execute.
  - `gauges`: List of Prometheus gauges to create from the query results.
    - `name`: Name of the gauge.
    - `desc`: Description of the gauge.
    - `col`: Column index in the query result to use as the gauge value.

- **`connections`**:
  - `db_host`: Db2 database host.
  - `db_name`: Db2 database name.
  - `db_port`: Db2 database port.
  - `db_user`: Db2 database user.
  - `db_passwd`: Db2 database password.
  - `extra_labels`: Additional labels to attach to Prometheus metrics.

---

## Running Locally

1. Ensure the `config.yaml` file is properly configured.
2. Run the application:
   ```bash
   python app.py config.yaml
   ```
3. The Prometheus metrics will be available at `http://localhost:9877/metrics`.

Example output of application startup:
```text
2023-01-07 10:24:16,858 - db2dexpo.prometheus - INFO - [GAUGE] [db2_applications_count] created
2023-01-07 10:24:16,859 - db2dexpo.prometheus - INFO - [GAUGE] [db2_lockwaits_count] created
2023-01-07 10:24:16,859 - db2dexpo.prometheus - INFO - [GAUGE] [db2_lockwaits_maxwait_seconds] created
2023-01-07 10:24:16,859 - db2dexpo.prometheus - INFO - [GAUGE] [db2_employees_created] created
2023-01-07 10:24:16,860 - db2dexpo.prometheus - INFO - Db2DExpo server started at port 9877
2023-01-07 10:24:17,232 - db2dexpo.db2 - INFO - [127.0.0.1:50000/sample] connected
```

---

## Running in Docker

1. Clone the repository:
   ```bash
   git clone https://github.com/Barryq93/db2Prom.git
   cd db2Prom
   ```

2. Build the Docker image:
   ```bash
   docker build -t db2prompy .
   ```

3. Run the container:
   ```bash
   docker run --name db2prom -it --env-file .env db2prompy
   ```

4. View the exported metrics:
   ```bash
   docker exec -it db2prom curl 127.0.0.1:9877
   ```

---

## Building an Executable with PyInstaller

To create a standalone executable for easier deployment:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Build the executable:
   ```bash
   pyinstaller --onefile app.py
   ```

3. The executable will be located in the `dist` directory. Run it like this:
   ```bash
   ./dist/app config.yaml
   ```

---

## Testing

The project includes unit tests to ensure the functionality of the application. To run the tests:

1. Install `pytest` and `pytest-asyncio`:
   ```bash
   pip install pytest pytest-asyncio
   ```

2. Run the tests:
   ```bash
   pytest tests/ -v
   ```

---

## Contributing

Contributions are welcome! If you'd like to contribute, please follow these steps:
1. Fork the repository.
2. Create a new branch for your feature or bugfix.
3. Submit a pull request with a detailed description of your changes.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Inspired by [db2dexpo](https://github.com/arapozojr/db2dexpo) by [arapozojr](https://github.com/arapozojr).
- Uses the [Prometheus Client](https://github.com/prometheus/client_python) for metric export.

---