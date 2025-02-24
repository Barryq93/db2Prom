from pydantic import BaseModel, ValidationError, constr, conint
from typing import List, Dict, Optional

class DB2ConnectionConfig(BaseModel):
    db_host: constr(strict=True)
    db_name: constr(strict=True)
    db_port: conint(gt=0, lt=65536)
    db_user: constr(strict=True)
    db_passwd: constr(strict=True)
    tags: List[str]
    extra_labels: Dict[str, str]
    ssl: bool = False
    ssl_ca_cert: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None

class GlobalConfig(BaseModel):
    log_level: constr(strict=True)
    retry_conn_interval: conint(gt=0)
    default_time_interval: conint(gt=0)
    log_path: constr(strict=True)
    port: conint(gt=0, lt=65536)

class QueryConfig(BaseModel):
    name: constr(strict=True)
    query: constr(strict=True)
    gauges: List[Dict]
    time_interval: conint(gt=0)

class Config(BaseModel):
    global_config: GlobalConfig
    connections: List[DB2ConnectionConfig]
    queries: List[QueryConfig]

def validate_config(config: dict) -> Config:
    """
    Validate the configuration dictionary using Pydantic.
    """
    try:
        return Config(**config)
    except ValidationError as e:
        raise ValueError(f"Configuration validation error: {e}")