import yaml

def generate_config():
    """
    Generate a sample config.yaml file.
    """
    config = {
        "global_config": {
            "log_level": "INFO",
            "retry_conn_interval": 60,
            "default_time_interval": 15,
            "log_path": "logs/",
            "port": 9844
        },
        "connections": [
            {
                "db_host": "localhost",
                "db_name": "sample_db",
                "db_port": 50000,
                "db_user": "db2inst1",
                "db_passwd": "encrypted_password_here",
                "tags": ["production"],
                "extra_labels": {
                    "dbinstance": "db2inst1",
                    "dbenv": "production"
                }
            }
        ],
        "queries": [
            {
                "name": "test_query",
                "query": "SELECT 1 FROM sysibm.sysdummy1",
                "time_interval": 10,
                "gauges": [
                    {
                        "name": "test_gauge",
                        "desc": "Test gauge",
                        "col": 1
                    }
                ]
            }
        ]
    }

    with open("config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

if __name__ == "__main__":
    generate_config()
    print("Sample config.yaml file generated.")