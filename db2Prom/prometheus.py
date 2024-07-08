from prometheus_client import start_http_server, Gauge
from prometheus_client.core import CollectorRegistry
from prometheus_client.exposition import MetricsHandler
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INVALID_LABEL_STR = "-"

# Custom logging middleware
class LoggingMetricsHandler(MetricsHandler):
    def do_GET(self):
        # Log the request
        logger.info(f"Received GET request from {self.client_address}")

        # Call the parent class method to handle the request
        super().do_GET()

# Custom Prometheus Exporter class
class CustomExporter:
    def __init__(self, port=9877):
        self.metric_dict = {}
        self.port = port  # Store port number
        self.registry = CollectorRegistry()

    def create_gauge(self, metric_name: str, metric_desc: str, metric_labels: list = []):
        try:
            if metric_labels:
                self.metric_dict[metric_name] = Gauge(metric_name, metric_desc, metric_labels, registry=self.registry)
            else:
                self.metric_dict[metric_name] = Gauge(metric_name, metric_desc, registry=self.registry)
            logger.info(f"[GAUGE] [{metric_name}] created")
        except Exception as e:
            logger.error(f"[GAUGE] [{metric_name}] failed to create: {e}")

    def set_gauge(self, metric_name: str, metric_value: float, metric_labels: dict = {}):
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
        try:
            # Start HTTP server with custom LoggingMetricsHandler
            start_http_server(self.port, registry=self.registry, handler=LoggingMetricsHandler)
            logger.info(f"Db2DExpo server started at port {self.port}")
        except Exception as e:
            logger.fatal(f"Failed to start Db2DExpo server at port {self.port}: {e}")
            raise e

# Example usage
if __name__ == "__main__":
    exporter = CustomExporter(port=9877)
    exporter.create_gauge("example_metric", "This is an example metric")
    exporter.set_gauge("example_metric", 1)
    exporter.start()
