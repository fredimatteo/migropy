from migropy.core.config import Config
from migropy.databases.base_adapter import BaseAdapter
from migropy.databases.commons import DbConfig
from migropy.databases.my_sql import MySql
from migropy.databases.postgres import Postgres


def get_db_connector(config: Config) -> BaseAdapter:
    db_type = config.db_type

    cf = DbConfig(
        host=config.db_host,
        port=config.db_port,
        user=config.db_user,
        password=config.db_password,
        database=config.db_name
    )

    if 'postgres' in db_type.lower():
        return Postgres(config=cf)
    elif 'mysql' in db_type.lower():
        return MySql(config=cf)

    raise ValueError(f"unsupported database type: {db_type}")
