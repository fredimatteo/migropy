import enum
import sys
from pathlib import Path

from migropy.configuration_parser import load_config
from migropy.core.logger import logger
from migropy.databases.services import get_db_connector
from migropy.migration_engine import MigrationEngine


class CommandsEnum(enum.StrEnum):
    INIT = "init"
    GENERATE = "generate"
    UPGRADE = "upgrade"
    DOWNGRADE = "downgrade"
    LIST_REVISIONS = "list"
    ROLLBACK = "rollback"


class Commands:
    """
    This class is used to define the commands that can be executed in the application from CLI.
    """
    def __init__(self, command: CommandsEnum):
        self.command = command

    def dispatch(self, **kwargs):
        """
        Dispatch the command to the appropriate method.
        """
        if not self.command:
            logger.error("No command provided.")
            sys.exit(1)

        match self.command:
            case CommandsEnum.INIT:
                if "project_name" in kwargs:
                    project_name = kwargs["project_name"]
                    self.__init(project_name)
                    return
                self.__init()
            case CommandsEnum.GENERATE:
                if "migration_name" not in kwargs:
                    logger.error("Migration name is required for generate command.")
                    sys.exit(1)

                migration_name = kwargs["migration_name"]
                self.__generate(migration_name)
            case CommandsEnum.UPGRADE:
                self.__upgrade()
            case CommandsEnum.DOWNGRADE:
                self.__downgrade()
            case CommandsEnum.LIST_REVISIONS:
                self.__list()
            case CommandsEnum.ROLLBACK:
                if "migrations_to_rollback" not in kwargs:
                    logger.error("Number of migrations to rollback is required.")
                    sys.exit(1)

                migrations_to_rollback = kwargs["migrations_to_rollback"]
                self.__rollback(migrations_to_rollback)
            case _:
                logger.error("Unknown command: %s", self.command)

    @staticmethod
    def __init(project_path: str = 'migropy'):
        try:
            import migropy

            package_dir = Path(migropy.__file__).resolve().parent
            template_dir = package_dir / "templates"

            if not template_dir.exists():
                raise FileNotFoundError(f"Template directory {template_dir} does not exist")

            ini_files = list(template_dir.glob("migropy.ini"))
            if not ini_files:
                raise FileNotFoundError("No .ini template file found in the templates directory")

            ini_content = ini_files[0].read_text(encoding="utf-8")
            Path("migropy.ini").write_text(ini_content, encoding="utf-8")

            python_files = list(template_dir.glob("migropy_env.py"))
            if not python_files:
                raise FileNotFoundError("No .py template file found in the templates directory")

            python_content = python_files[0].read_text(encoding="utf-8")
            Path("migropy_env.py").write_text(python_content, encoding="utf-8")

            versions_path = Path(project_path) / "versions"
            versions_path.mkdir(parents=True, exist_ok=True)

            logger.info("Project initialized successfully.")

        except Exception as e:
            logger.error("Error during project initialization: %s", str(e))
            sys.exit(1)

    @staticmethod
    def __generate(migration_name: str):
        db = get_db_connector(load_config())
        migration_engine = MigrationEngine(db, load_config())

        migration_engine.init()
        migration_engine.generate_revision(migration_name)

    @staticmethod
    def __upgrade():
        db = get_db_connector(load_config())

        migration_engine = MigrationEngine(db, load_config())
        migration_engine.upgrade()

    @staticmethod
    def __downgrade():
        db = get_db_connector(load_config())

        migration_engine = MigrationEngine(db, load_config())
        migration_engine.downgrade()

    @staticmethod
    def __list():
        revisions = MigrationEngine(config=load_config()).list_revisions()
        for revision in revisions:
            print('- ' + revision.name)

    @staticmethod
    def __rollback(migrations_to_rollback: int):
        db = get_db_connector(load_config())

        migration_engine = MigrationEngine(db, load_config())
        migration_engine.rollback(migrations_to_rollback)