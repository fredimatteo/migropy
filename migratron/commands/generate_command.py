from migratron.configuration_parser import load_db_config
from migratron.databases.services import get_db_connector
from migratron.migration_engine import MigrationEngine


def generate_command(migration_name: str):
    db = get_db_connector(load_db_config())

    mg = MigrationEngine(db)

    mg.init()

    mg.generate_revision(migration_name)
    print('Migration completed successfully')