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
- **Database Reachability Monitoring**: Added a new metric (db2_connection_status) to track whether the database is reachable (1 = reachable, 0 = unreachable).

# Changes from db2dexpo

## Enhanced Logging and Error Handling
- Improved logging messages throughout the application for better clarity and error reporting.
- Added comprehensive error handling mechanisms to gracefully manage exceptions and errors.

## Extended Metrics Export

- Expanded the metrics export functionality to include additional database performance metrics beyond standard connections.
- Introduced flexibility in defining and exporting metrics based on user-defined queries and configurations.
Added a new metric (db2_connection_status) to monitor database reachability.

## Configuration Flexibility

- Enhanced configuration options via YAML files to provide more dynamic setup capabilities.
- Users can now easily define and customize database connections, queries, and metrics through configurable YAML files.

## Bug Fixes and Optimization

- Optimized codebase for improved performance and reliability.
- Fixed issues with non-UTF-8 characters in the codebase.
- Improved handling of database connection failures.

## Documentation and Readme Updates
- Updated README.md to reflect changes, installation instructions, and usage guidelines specific to db2Prom.
- Added comprehensive examples and outputs to demonstrate usage scenarios, including Docker setup and metric visualization.
- Added instructions for building the application locally using PyInstaller.

Grateful to arapozojr for their initial work on db2dexpo, which served as the foundation for this project.

## Running Locally

To run db2Prom locally, follow these steps:

### Prerequisites

- Python 3.10.8 or higher
- pip (Python package installer)

## Installation
Clone the repository:

```bash
git clone https://github.com/Barryq93/db2Prom.git
cd db2Prom
```

Install all required packages using pip:

```shell
pip3 install -r requirements.txt
```

Check the example config YAML on how to handle multiple databases with different access. Use this example YAML to also make your own config.yaml file, with your queries and gauge metrics.

Run the application:

```shell
python app.py config.yaml
```
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
You can then open http://localhost:9877/ and see the exported metrics.

Ctrl+c will stop the application.

## Building the Application Locally
To build the application into a single executable using PyInstaller, follow these steps:

Prerequisites
Python 3.10.8 or higher
pip (Python package installer)

### Installation
Install PyInstaller:

```bash
pip install pyinstaller
```

### Build the Executable
Navigate to your project directory and run the following command:

```bash
pyinstaller --onefile app.py
```

This will create a single executable file in the dist/ directory.

Run the Executable
Navigate to the dist/ directory and run the executable:

On Windows:
```bash
cd dist
app.exe
```

On macOS/Linux:
``` bash
cd dist
./app
```
Advanced Options
Here are some additional PyInstaller options you might find useful:

``` Text
Option	Description
--name=<name>	Specify the name of the executable (default: same as the script name).
--icon=<icon.ico>	Add an icon to the executable (Windows only).
--windowed	Build a GUI application without a console window (Windows/macOS).
--add-data=<src;dest>	Include additional files or directories in the build.
--clean	Clean the build directory before building.
--debug	Build the executable in debug mode.
Example with advanced options:
```

```bash
pyinstaller --onefile --name=myapp --icon=app.ico --windowed --clean app.py
```
## Running in Docker

Clone this repo:

```shell
git clone https://github.com/Barryq93/db2Prom.git
```cd db2Prom/

Check the example config YAML on how to handle multiple databases with different access. Use this example YAML to also make your own config.yaml file, with your queries and gauge metrics.

Build Docker image:

```shell
docker build -t db2prompy .
```

Run a container:

```shell
docker run --name db2prompy -it --env-file .env db2prompy
```
See the exported metrics:

```shell
docker exec -it db2prompy curl 127.0.0.1:9877
```
Example output:

``` text
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
