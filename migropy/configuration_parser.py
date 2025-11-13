import configparser
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from migropy.core.config import Config
from migropy.core.logger import logger


def load_config(config_file_path: str = "migropy.ini") -> Config:
    load_dotenv()

    config_path = Path(os.getcwd()).joinpath(config_file_path)

    if not config_path.exists():
        logger.error(f"FAILED: No config file '{config_file_path}' found")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_file_path)

    def env(name, fallback):
        return os.getenv(name, fallback)

    cf = Config(
        db_host=env("MIGRO_DB_HOST", config.get("database", "host", fallback="")),
        db_port=int(env("MIGRO_DB_PORT", config.get("database", "port", fallback=0))),
        db_user=env("MIGRO_DB_USER", config.get("database", "user", fallback="")),
        db_password=env("MIGRO_DB_PASSWORD", config.get("database", "password", fallback="")),
        db_name=env("MIGRO_DB_NAME", config.get("database", "dbname", fallback="")),
        db_type=env("MIGRO_DB_TYPE", config.get("database", "type", fallback="")),
        script_location=env("MIGRO_SCRIPT_LOCATION",
                            config.get("migrations", "script_location", fallback='migrations')),
        logger_level=env("MIGRO_LOGGER_LEVEL", config.get("logger", "level", fallback='INFO')),
    )

    return cf
