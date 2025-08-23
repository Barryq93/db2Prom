from prometheus_client import (
    start_http_server,
    Gauge,
    CollectorRegistry,
)
import logging
import socket
import time

logger = logging.getLogger(__name__)

INVALID_LABEL_STR = "-"


class CustomExporter:
    def __init__(
        self,
        port: int = 9877,
        host: str | None = None,
        query_names: list | None = None,
    ):
        """Initialize the Prometheus exporter.

        Parameters
        ----------
        port : int
            Port where the exporter will expose metrics.
        host : str, optional
            Network interface to bind the HTTP server to. If not provided,
            the exporter will bind to the current machine's hostname.
        query_names : list, optional
            Sanitized query names from the configuration. A cache of last
            successful run timestamps will be initialised with these names to
            ensure metrics exist even before a query runs.
        """
        self.metric_dict: dict[str, Gauge] = {}
        self.port = port
        self.host = host or socket.gethostname()
        # Use a dedicated registry so metrics from different exporter instances
        # do not conflict with each other.
        self.registry = CollectorRegistry()
        self.query_last_success: dict[str, float] = {}

        # Create default metrics
        self.create_gauge(
            "db2_connection_status",
            "Indicates whether the DB2 database is reachable (1 = reachable, 0 = unreachable)",
        )

        self.create_gauge(
            "db2_query_timeout",
            "Indicates that a query execution has timed out (1 = timeout)",
            ["query"],
        )

        # Initialize cache for each configured query
        if query_names:
            for q in query_names:
                self.query_last_success[q] = 0.0

    def create_gauge(
        self,
        metric_name: str,
        metric_desc: str,
        metric_labels: list | None = None,
    ):
        """Create a new Prometheus gauge metric."""
        metric_labels = metric_labels or []
        try:
            if metric_labels:
                gauge = Gauge(
                    metric_name, metric_desc, metric_labels, registry=self.registry
                )
            else:
                gauge = Gauge(metric_name, metric_desc, registry=self.registry)
            self.metric_dict[metric_name] = gauge
            logger.info(f"[GAUGE] [{metric_name}] created")
        except ValueError as e:
            # If a metric with the same name was already registered in this
            # registry, simply reuse the existing one instead of failing.
            logger.warning(f"[GAUGE] [{metric_name}] already exists: {e}")
        except Exception as e:
            logger.error(f"[GAUGE] [{metric_name}] failed to create: {e}")

    def set_gauge(self, metric_name: str, metric_value: float, metric_labels: dict = {}):
        """
        Set the value of a Prometheus gauge metric.
        """
        try:
            if metric_labels:
                self.metric_dict[metric_name].labels(**metric_labels).set(metric_value)
            else:
                self.metric_dict[metric_name].set(metric_value)
            labels_str = ', '.join(f'{key}: "{value}"' for key, value in metric_labels.items())
            logger.debug(f"[GAUGE] [{metric_name}{{{labels_str}}}] {metric_value}")
        except Exception as e:
            logger.error(f"[GAUGE] [{metric_name}] failed to update: {e}")

    def record_query_duration(self, query: str, duration: float) -> None:
        """Record execution time for a query."""
        self.set_gauge("db2_query_duration_seconds", duration, {"query": query})

    def record_query_success(self, query: str) -> None:
        """Update the last successful run timestamp for a query."""
        timestamp = time.time()
        self.query_last_success[query] = timestamp
        self.set_gauge("db2_query_last_success_timestamp", timestamp, {"query": query})

    def start(self):
        """Start the Prometheus HTTP server."""
        try:
            # Start HTTP server on specified port and host
            start_http_server(self.port, addr=self.host, registry=self.registry)
            logger.info(f"Db2Prom server started at {self.host}:{self.port}")
        except Exception as e:
            logger.fatal(
                f"Failed to start Db2Prom server at {self.host}:{self.port}: {e}"
            )
            raise e
