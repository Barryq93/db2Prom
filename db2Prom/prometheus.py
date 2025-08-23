from prometheus_client import start_http_server, Gauge, REGISTRY
import logging
import socket

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INVALID_LABEL_STR = "-"


class CustomExporter:
    def __init__(self, port=9877, host=None):
        """Initialize the Prometheus exporter.

        Parameters
        ----------
        port : int
            Port where the exporter will expose metrics.
        host : str, optional
            Network interface to bind the HTTP server to. If not provided,
            the exporter will bind to the current machine's hostname.
        """
        self.metric_dict = {}
        self.port = port
        self.host = host or socket.gethostname()
        # Check if the metric already exists before creating it
        if "db2_connection_status" not in REGISTRY._names_to_collectors:
            self.create_gauge(
                "db2_connection_status",
                "Indicates whether the DB2 database is reachable (1 = reachable, 0 = unreachable)",
            )

    def create_gauge(self, metric_name: str, metric_desc: str, metric_labels: list = []):
        """
        Create a new Prometheus gauge metric.
        """
        try:
            if metric_labels:
                self.metric_dict[metric_name] = Gauge(metric_name, metric_desc, metric_labels)
            else:
                self.metric_dict[metric_name] = Gauge(metric_name, metric_desc)
            logger.info(f"[GAUGE] [{metric_name}] created")
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

    def start(self):
        """Start the Prometheus HTTP server."""
        try:
            # Start HTTP server on specified port and host
            start_http_server(self.port, addr=self.host)
            logger.info(f"Db2Prom server started at {self.host}:{self.port}")
        except Exception as e:
            logger.fatal(
                f"Failed to start Db2Prom server at {self.host}:{self.port}: {e}"
            )
            raise e
