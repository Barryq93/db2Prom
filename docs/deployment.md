# Deployment Guide

This guide provides step-by-step instructions for deploying the DB2 Prometheus Exporter.

---

## Prerequisites

Before deploying the application, ensure the following prerequisites are met:

1. **Python 3.8 or higher**: The application is written in Python and requires Python 3.8 or later.
2. **IBM DB2 Client Libraries**: Install the IBM DB2 client libraries and ensure they are properly configured.
3. **Prometheus Server**: A Prometheus server must be running to scrape metrics from the exporter.
4. **Configuration File**: A valid `config.yaml` file must be created and configured.

---

## Steps for Deployment

### 1. Clone the Repository
Clone the repository to your local machine or server:

```bash
git clone https://github.com/Barryq93/db2Prom.git
cd db2Prom
```

2. Install Dependencies
Install the required Python dependencies using pip:

``` bash
pip install -r requirements.txt
```

3. Generate a Configuration File

If you don't already have a config.yaml file, generate one using the provided script:

``` bash
python scripts/generate_config.py
```

Edit the generated config.yaml file to include your DB2 connection details and queries.

4. Start the Application
Run the application using the following command:

``` bash
python app.py config.yaml
```

The application will start and begin exporting metrics to Prometheus.

5. Access Prometheus Metrics
The Prometheus metrics endpoint is exposed on port 9844 by default. You can access it at:

http://localhost:9844/metrics

6. Configure Prometheus
Add the exporter to your Prometheus configuration file (prometheus.yml):

```yaml
scrape_configs:
  - job_name: 'db2_exporter'
    static_configs:
      - targets: ['localhost:9844']
```

Restart the Prometheus server to start scraping metrics from the exporter.

Deployment Options
Docker Deployment
Build the Docker image:

``` bash
docker build -t db2-prometheus-exporter .
```
Run the Docker container:

``` bash
docker run -d -p 9844:9844 --name db2-exporter db2-prometheus-exporter
```

Kubernetes Deployment
Create a Kubernetes deployment file (db2-exporter-deployment.yaml):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: db2-exporter
spec:
  replicas: 1
  selector:
    matchLabels:
      app: db2-exporter
  template:
    metadata:
      labels:
        app: db2-exporter
    spec:
      containers:
      - name: db2-exporter
        image: db2-prometheus-exporter
        ports:
        - containerPort: 9844
```

Deploy to Kubernetes:

```bash
kubectl apply -f db2-exporter-deployment.yaml
```

Verifying the Deployment
Check the application logs to ensure it is running without errors.


Verify that Prometheus is scraping metrics from the exporter by querying the metrics in the Prometheus UI.

Troubleshooting
If you encounter issues during deployment, refer to the Troubleshooting Guide for common solutions.

Next Steps
Configure alerts in Prometheus based on the exported metrics.

Integrate with Grafana for visualization of DB2 metrics.


---

### **Summary**
This `deployment.md` file provides a comprehensive guide for deploying the DB2 Prometheus Exporter, including prerequisites, steps for deployment, Docker and Kubernetes deployment options, and verification steps. Let me know if you need further assistance!