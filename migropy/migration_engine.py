import sys
import uuid
from io import StringIO
from pathlib import Path
from typing import List, Optional, Final

from migropy.core.config import default_config, Config
from migropy.core.logger import logger
from migropy.databases.base_adapter import BaseAdapter


class MigrationConstants:
    """Immutable constants used for managing SQL migration scripts."""
    FIRST_REVISION_ID: Final[str] = '0000'
    UP_PREFIX: Final[str] = "-- Up"
    COMMENT_PREFIX: Final[str] = "--"
    DOWN_PREFIX: Final[str] = "-- Down"
    REVISION_TEMPLATE: Final[list[str]] = [
        "-- Up migration",
        "\n",
        "\n",
        "-- Down migration"
    ]


class MigrationEngine:
    """
    MigrationEngine is responsible for managing SQL database schema migrations.

    It handles creation of the migration tracking table, generation of revision files,
    application of upgrade and downgrade scripts, and maintaining metadata about
    executed migrations.
    """

    def __init__(self, db: Optional[BaseAdapter] = None, config: Optional['Config'] = default_config):
        """
        Initialize the migration engine with an optional database connector and migration directory.

        :param db: Optional DatabaseConnector instance for SQL execution.
        :param config: Optional configuration object. If not provided, a default configuration is used.
        """
        self.db: Optional[BaseAdapter] = db
        self.is_postgres = config.db_type == 'postgres'
        self.base_schema = config.base_schema
        self.migration_dir: Path = Path(config.script_location).resolve()

    def init(self):
        """
        Initialize the migration infrastructure by creating the migration metadata table.
        """
        self.__create_migration_table()

    def generate_revision(self, revision_name: str = "") -> None:
        """
        Generates a new migration revision file.

        :param revision_name: Name for the migration; if empty, a UUID is used.
        """
        for char in revision_name:
            if not char.isalnum() and char != " " and char != "_":
                logger.error('invalid revision name. Only alphanumeric characters, spaces and underscores are allowed')
                sys.exit(1)

        revision_name = revision_name.replace(" ", "_")
        if revision_name == "":
            revision_name = str(uuid.uuid4())

        self.__create_revision_file(revision_name)

    def list_revisions(self) -> List[Path]:
        """
        Lists all available migration revision files, sorted by revision ID.

        :return: Sorted list of Path objects.
        """
        files: List[Path] = [obj for obj in self.migration_dir.joinpath('versions').iterdir() if obj.is_file()]
        return sorted(files, key=lambda x: x.name.split("_")[0])

    def upgrade(self) -> None:
        """
        Applies all up migration scripts in order.
        Each script is parsed to extract SQL statements from the "-- Up" section.
        """
        revisions = self.list_revisions()
        for revision in revisions:
            lines = revision.read_text().splitlines()
            builder = StringIO()
            for line in lines:
                line = line.strip()
                if line.startswith(MigrationConstants.UP_PREFIX):
                    continue
                if line.startswith(MigrationConstants.DOWN_PREFIX):
                    break
                if not line.startswith(MigrationConstants.COMMENT_PREFIX):
                    builder.writelines([line, "\n"])

            try:
                self.db.execute(builder.getvalue())
                self.db.commit()
            except Exception as e:
                logger.error(f"Error while upgrading migration {revision.name}: {e}")
                self.db.rollback()
                sys.exit(1)

        last_revision_name = self.__get_last_revision_name()
        self.upsert_migration_table(last_revision_name)

    def downgrade(self) -> None:
        """
        Applies all down migration scripts in reverse order.
        Each script is parsed to extract SQL statements from the "-- Down" section.
        """
        revisions = self.list_revisions()
        revisions.reverse()
        for revision in revisions:
            lines = revision.read_text().splitlines()
            builder = StringIO()
            is_down = False
            for line in lines:
                line = line.strip()
                if line.startswith(MigrationConstants.DOWN_PREFIX):
                    is_down = True
                    continue
                if not line.startswith(MigrationConstants.COMMENT_PREFIX) and is_down:
                    builder.write(line)
                    builder.write("\n")

            try:
                self.db.execute(builder.getvalue())
                self.db.commit()
            except Exception as e:
                logger.error(f"Error while downgrading migration {revision.name}: {e}")
                self.db.rollback()
                sys.exit(1)

        last_revision_name = self.__get_last_revision_name(is_downgrade=True)
        self.upsert_migration_table(last_revision_name)

    def rollback(self, migrations_to_rollback: int = 1) -> None:
        """
        Rolls back the last 'n' applied migrations by executing the corresponding down scripts.

        :param migrations_to_rollback: Number of migrations to rollback, starting from the last applied.
        """
        if not self.__at_least_one_revision_executed():
            print('Error: No migrations have been executed yet.')
            sys.exit(1)

        executed_revision_name = self.__get_last_revision_executed_name()
        if not executed_revision_name:
            print('Error: Unable to retrieve the last executed migration.')
            sys.exit(1)

        all_revisions = self.list_revisions()
        executed_index = next((i for i, rev in enumerate(all_revisions) if executed_revision_name in rev.name), None)

        if executed_index is None:
            print('Error: Executed revision not found in revision files.')
            sys.exit(1)

        applicable_revisions = all_revisions[:executed_index + 1][-migrations_to_rollback:]
        applicable_revisions.reverse()

        if migrations_to_rollback > len(applicable_revisions):
            print(f'Error: Cannot rollback {migrations_to_rollback} migrations. Only {len(applicable_revisions)} available.')
            sys.exit(1)

        for revision in applicable_revisions:
            lines = revision.read_text().splitlines()
            builder = StringIO()
            is_down = False
            for line in lines:
                line = line.strip()
                if line.startswith(MigrationConstants.DOWN_PREFIX):
                    is_down = True
                    continue
                if not line.startswith(MigrationConstants.COMMENT_PREFIX) and is_down:
                    builder.write(line + "\n")

            try:
                self.db.execute(builder.getvalue())
                self.db.commit()
            except Exception as e:
                logger.error(f"Error while rolling back migration {revision.name}: {e}")
                self.db.rollback()
                sys.exit(1)

        new_last_index = executed_index - migrations_to_rollback

        if new_last_index < 0:
            if self.is_postgres:
                statement = f"DELETE FROM {self.base_schema}.migrations"
            else:
                statement = "DELETE FROM migrations"

            self.db.execute(statement)
        else:
            new_revision_name = all_revisions[new_last_index].name
            self.upsert_migration_table(new_revision_name)

        self.db.commit()

    def upsert_migration_table(self, revision_name: str) -> None:
        """
        Inserts or updates the 'migrations' table with the latest applied revision.

        :param revision_name: The name of the last executed revision file.
        """
        if not self.__at_least_one_revision_executed():
            if self.is_postgres:
                statement = f"""INSERT INTO {self.base_schema}.migrations (name) VALUES ('{revision_name}')"""
            else:
                statement = f"""INSERT INTO migrations (name) VALUES ('{revision_name}')"""

            self.db.execute(statement)
        else:
            if self.is_postgres:
                statement = f"""UPDATE {self.base_schema}.migrations SET name = '{revision_name}'"""
            else:
                statement = f"""UPDATE migrations SET name = '{revision_name}'"""

            self.db.execute(statement)

        self.db.commit()

    def __create_migration_table(self) -> None:
        """
        Creates the 'migrations' table if it does not exist.
        This table tracks the latest executed revision.
        """
        if self.db:
            logger.debug('creating migrations table')

            if self.is_postgres:
                statement = f"""
                CREATE TABLE IF NOT EXISTS {self.base_schema}.migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            else:
                statement = """
                    CREATE TABLE IF NOT EXISTS migrations (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """

            self.db.execute(statement)
            self.db.commit()

    def __create_revision_file(self, revision_name: str) -> None:
        """
        Creates a new revision SQL file with up and down sections.

        :param revision_name: Name of the revision.
        """
        revision_id = self.__get_last_revision_id()
        revision_id = str(int(revision_id) + 1).zfill(4)

        revision_file_name = f"{revision_id}_{revision_name}.sql"
        revision_file_path = self.migration_dir / 'versions' / revision_file_name

        self.migration_dir.mkdir(parents=True, exist_ok=True)
        with open(revision_file_path, "w", encoding='utf-8') as revision_file:
            revision_file.writelines(MigrationConstants.REVISION_TEMPLATE)

    def __get_last_revision_id(self) -> str:
        """
        Returns the ID of the most recent migration revision.

        :return: Zero-padded numeric string representing the last revision ID.
        """
        file_names: List[str] = [obj.name for obj in self.migration_dir.joinpath('versions').iterdir() if obj.is_file()]
        file_names_prefix = [file_name.split("_")[0] for file_name in file_names]
        if not file_names_prefix:
            return MigrationConstants.FIRST_REVISION_ID
        file_names_prefix.sort()
        return file_names_prefix[-1]

    def __get_last_revision_name(self, is_downgrade: bool = False) -> str:
        """
        Returns the filename of the most recent (or oldest if downgrade) revision.

        :param is_downgrade: If True, fetches the first revision instead of the last.
        :return: Filename of the revision.
        """
        file_names: List[str] = [obj.name for obj in self.migration_dir.joinpath('versions').iterdir() if obj.is_file()]
        file_names.sort()
        return file_names[-1] if not is_downgrade else file_names[0]

    def __at_least_one_revision_executed(self) -> bool:
        """
        Checks if at least one migration has already been executed.

        :return: True if the migrations table contains any rows.
        """
        logger.debug('checking if at least one revision has been executed')

        if self.is_postgres:
            statement = f"SELECT COUNT(*) FROM {self.base_schema}.migrations"
        else:
            statement = "SELECT COUNT(*) FROM migrations"

        result = self.db.execute(statement)
        return result.fetchone()[0] > 0

    def __get_last_revision_executed_name(self) -> str | None:
        """
        Retrieves the last executed revision from the migrations table.

        :return: The name of the last executed revision.
        """
        if self.is_postgres:
            statement = f"SELECT name FROM {self.base_schema}.migrations"
        else:
            statement = "SELECT name FROM migrations"

        result = self.db.execute(statement)
        result = result.fetchone()
        if len(result) > 0:
            return result[0]

        return None
