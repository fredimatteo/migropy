# Template for environment setup configuration

# Database connection settings
# available types: postgres, mysql
DB_HOST: str = ''
DB_PORT: int = 0
DB_USER: str = ''
DB_PASSWORD: str = ''
DB_NAME: str = ''
DB_TYPE: str = ''

# Migrations
# path to migration scripts
# use forward slashes (/) also on windows to provide an os agnostic path
SCRIPT_LOCATION: str = 'migropy'
# option available with postgres
BASE_SCHEMA: str = 'public'

# Logger settings
# available levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOGGER_LEVEL: str = 'INFO'


__all__ = [
    "DB_HOST",
    "DB_PORT",
    "DB_USER",
    "DB_PASSWORD",
    "DB_NAME",
    "DB_TYPE"
]