from prometheus_client import start_http_server, Gauge
from prometheus_client.exposition import MetricsHandler
import logging
import socketserver
import http.server

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Custom MetricsHandler that logs each request
class LoggingMetricsHandler(MetricsHandler):
    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s\n" % (
            self.client_address[0],
            self.log_date_time_string(),
            format % args))

    def do_GET(self):
        logger.info(f"Received GET request from {self.client_address}")
        super().do_GET()

# Custom Prometheus Exporter class
class CustomExporter:
    def __init__(self, port=9877):
        self.metric_dict = {}
        self.port = port  # Store port number

    def create_gauge(self, metric_name: str, metric_desc: str, metric_labels: list = []):
        try:
            if metric_labels:
                self.metric_dict[metric_name] = Gauge(metric_name, metric_desc, metric_labels)
            else:
                self.metric_dict[metric_name] = Gauge(metric_name, metric_desc)
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
            start_http_server(self.port, handler_class=LoggingMetricsHandler)
            logger.info(f"Prometheus HTTP server started at port {self.port}")
            # Block indefinitely to keep the server running
            socketserver.TCPServer.allow_reuse_address = True
            socketserver.TCPServer(('localhost', self.port), LoggingMetricsHandler).serve_forever()

        except Exception as e:
            logger.fatal(f"Failed to start Prometheus HTTP server at port {self.port}: {e}")
            raise e
