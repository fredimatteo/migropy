import configparser
import importlib.util
import os
import sys
from pathlib import Path

from migropy.core.config import Config
from migropy.core.logger import logger


def load_config(config_file_path: str = "migropy.ini") -> Config:
    config_path = Path(os.getcwd()).joinpath(config_file_path)

    if not config_path.exists():
        logger.error(f"FAILED: No config file '{config_file_path}' found")
        sys.exit(1)

    if config_path.suffix == ".py":
        return _load_py_config(config_path)

    return _load_ini_config(config_path)


def _load_ini_config(config_path: Path) -> Config:
    config = configparser.ConfigParser()
    config.read(config_path)

    try:
        cf = Config(
            db_host=config.get("database", "host", fallback=''),
            db_port=config.getint("database", "port", fallback=0),
            db_user=config.get("database", "user", fallback=''),
            db_password=config.get("database", "password", fallback=''),
            db_name=config.get("database", "dbname", fallback=''),
            db_type=config.get("database", "type", fallback=''),
            script_location=config.get("migrations", "script_location", fallback='migrations'),
            logger_level=config.get("logger", "level", fallback='INFO')
        )
    except configparser.NoSectionError as e:
        logger.error('missing configuration section in config file: %s', str(e))
        sys.exit(1)

    return cf


def _load_py_config(config_path: Path) -> Config:
    spec = importlib.util.spec_from_file_location("migropy_user_config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    cf = Config(
        db_host=getattr(module, "DB_HOST"),
        db_port=getattr(module, "DB_PORT"),
        db_user=getattr(module, "DB_USER"),
        db_password=getattr(module, "DB_PASSWORD"),
        db_name=getattr(module, "DB_NAME"),
        db_type=getattr(module, "DB_TYPE"),
        script_location=getattr(module, "SCRIPT_LOCATION", "migropy"),
        logger_level=getattr(module, "LOGGER_LEVEL", "INFO"),
    )

    return cf
