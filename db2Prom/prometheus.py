from prometheus_client import start_http_server, Gauge, REGISTRY
import logging

logger = logging.getLogger(__name__)

INVALID_LABEL_STR = "-"

class CustomExporter:
    def __init__(self, port=9877, prefix="db2_"):
        """
        Initialize the Prometheus exporter.
        """
        self.metric_dict = {}
        self.port = port
        self.prefix = prefix

    def create_gauge(self, metric_name: str, metric_desc: str, metric_labels: list = []):
        """
        Create a new Prometheus gauge metric.
        """
        full_name = f"{self.prefix}{metric_name}"
        try:
            if metric_labels:
                self.metric_dict[full_name] = Gauge(full_name, metric_desc, metric_labels)
            else:
                self.metric_dict[full_name] = Gauge(full_name, metric_desc)
            logger.info(f"[GAUGE] [{full_name}] created")
        except Exception as e:
            logger.error(f"[GAUGE] [{full_name}] failed to create: {e}")

    def set_gauge(self, metric_name: str, metric_value: float, metric_labels: dict = {}):
        """
        Set the value of a Prometheus gauge metric.
        """
        full_name = f"{self.prefix}{metric_name}"
        try:
            if metric_labels:
                self.metric_dict[full_name].labels(**metric_labels).set(metric_value)
            else:
                self.metric_dict[full_name].set(metric_value)
            labels_str = ', '.join(f'{key}: "{value}"' for key, value in metric_labels.items())
            logger.debug(f"[GAUGE] [{full_name}{{{labels_str}}}] {metric_value}")
        except Exception as e:
            logger.error(f"[GAUGE] [{full_name}] failed to update: {e}")

    def start(self):
        """
        Start the Prometheus HTTP server.
        """
        try:
            start_http_server(self.port)
            logger.info(f"Db2Prom server started at port {self.port}")
        except Exception as e:
            logger.fatal(f"Failed to start Db2Prom server at port {self.port}: {e}")
            raise e