from prometheus_client import start_http_server, Gauge
from prometheus_client.exposition import BaseHTTPRequestHandler
import logging
import os
import socketserver

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

INVALID_LABEL_STR = "-"

# Custom HTTPRequestHandler class to log each request
class LoggingHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info("%s - - [%s] %s\n" % (
            self.client_address[0],
            self.log_date_time_string(),
            format % args))

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
            # Start HTTP server with custom LoggingHTTPRequestHandler
            server = socketserver.TCPServer(('', self.port), LoggingHTTPRequestHandler)
            logger.info(f"Db2DExpo server started at port {self.port}")
            server.serve_forever()
        except Exception as e:
            logger.fatal(f"Failed to start Db2DExpo server at port {self.port}: {e}")
            raise e

# Example usage
if __name__ == "__main__":
    exporter = CustomExporter(port=9877)
    exporter.create_gauge("example_metric", "This is an example metric")
    exporter.set_gauge("example_metric", 1)
    exporter.start()
