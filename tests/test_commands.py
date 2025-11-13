import sys
import types

import pytest

from migropy.commands.command import Commands, CommandsEnum
from migropy.databases.commons import DbConfig
from migropy.databases.postgres import Postgres
from tests import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, DB_PORT


@pytest.fixture
def mock_migropy_module(tmp_path, monkeypatch):
    fake_package_dir = tmp_path / "migropy"
    fake_package_dir.mkdir()
    (fake_package_dir / "__init__.py").write_text("")

    templates_dir = fake_package_dir / "templates"
    templates_dir.mkdir()

    # INI file
    (templates_dir / "migropy.ini").write_text(
        f"""
        [database]
        host = {DB_HOST}
        port = {DB_PORT}
        user = {DB_USER}
        password = {DB_PASSWORD}
        dbname = {DB_NAME}
        type = postgres

        [migrations]
        script_location = migropy
        base_schema = public

        [logger]
        level = DEBUG
    """,
        encoding="utf-8",
    )

    # Python env file
    (templates_dir / "migropy_env.py").write_text("DB_TYPE = 'sqlite'", encoding="utf-8")

    sys.modules["migropy"] = types.SimpleNamespace(
        __file__=str(fake_package_dir / "__init__.py")
    )

    return templates_dir


@pytest.fixture
def initialized_project(tmp_path, mock_migropy_module, monkeypatch):
    monkeypatch.chdir(tmp_path)

    cmd = Commands(CommandsEnum.INIT)
    cmd.dispatch()

    versions_dir = tmp_path / "migropy" / "versions"
    assert versions_dir.exists()

    return tmp_path, versions_dir


@pytest.fixture(autouse=True)
def db_instance():
    db = Postgres(
        DbConfig(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
    )
    yield db
    print("Cleaning up database...")
    db.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")


# -----------------------------------------------------------------------------


def test_init_command_success(initialized_project):
    project_path, versions_dir = initialized_project

    assert (project_path / "migropy.ini").exists()
    assert versions_dir.exists()


def test_init_command_missing_template_dir(tmp_path, monkeypatch, mocker):
    fake_package_dir = tmp_path / "migropy"
    fake_package_dir.mkdir()
    (fake_package_dir / "__init__.py").write_text("")

    sys.modules["migropy"] = types.SimpleNamespace(
        __file__=str(fake_package_dir / "__init__.py")
    )

    monkeypatch.chdir(tmp_path)

    mock_exit = mocker.patch("sys.exit")

    cmd = Commands(CommandsEnum.INIT)
    cmd.dispatch()

    mock_exit.assert_called_once_with(1)


def test_generate_revision(initialized_project):
    project_path, versions_dir = initialized_project

    cmd = Commands(CommandsEnum.GENERATE)
    cmd.dispatch(migration_name="create_users_table")

    generated_files = list(versions_dir.glob("*.sql"))
    assert len(generated_files) == 1


def test_apply_one_migration(initialized_project, db_instance):
    project_path, versions_dir = initialized_project

    # Generate migration file
    cmd = Commands(CommandsEnum.GENERATE)
    cmd.dispatch(migration_name="create_users_table")

    migration_file = next(versions_dir.glob("*.sql"))
    migration_file.write_text(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL
        );
        """,
        encoding="utf-8",
    )

    # Apply migrations
    cmd = Commands(CommandsEnum.UPGRADE)
    cmd.dispatch()

    cursor = db_instance.execute("SELECT * FROM users")
    assert cursor is not None
    assert list(cursor.fetchall()) == []


def test_apply_multiple_migrations(initialized_project, db_instance):
    project_path, versions_dir = initialized_project

    cmd = Commands(CommandsEnum.GENERATE)

    # Create migrations
    cmd.dispatch(migration_name="create_users_table")
    cmd.dispatch(migration_name="add_age_to_users")

    generated_files = sorted(versions_dir.glob("*.sql"))
    assert len(generated_files) == 2

    # First migration
    generated_files[0].write_text(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL
        );
        """,
        encoding="utf-8",
    )

    # Second migration
    generated_files[1].write_text(
        "ALTER TABLE users ADD COLUMN age INT;", encoding="utf-8"
    )

    # Apply upgrades
    cmd = Commands(CommandsEnum.UPGRADE)
    cmd.dispatch()

    cursor = db_instance.execute("SELECT age FROM users")
    assert cursor is not None
    assert list(cursor.fetchall()) == []


def test_downgrade_base(initialized_project, db_instance):
    project_path, versions_dir = initialized_project

    cmd = Commands(CommandsEnum.GENERATE)

    # Create migrations
    cmd.dispatch(migration_name="create_users_table")
    cmd.dispatch(migration_name="add_age_to_users")

    generated_files = sorted(versions_dir.glob("*.sql"))
    assert len(generated_files) == 2

    # First migration
    generated_files[0].write_text(
        """
        -- Up migration
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL
        );
        -- Down migration
        DROP TABLE IF EXISTS users;
        """,
        encoding="utf-8",
    )

    # Second migration
    generated_files[1].write_text(
        """
        -- Up migration
        ALTER TABLE users ADD COLUMN age INT;
        -- Down migration
        ALTER TABLE users DROP COLUMN age;
        """,
        encoding="utf-8",
    )

    # Apply upgrades
    cmd = Commands(CommandsEnum.UPGRADE)
    cmd.dispatch()

    cursor = db_instance.execute("SELECT age FROM users")
    assert cursor is not None
    assert list(cursor.fetchall()) == []

    # Downgrade to base
    cmd = Commands(CommandsEnum.DOWNGRADE)
    cmd.dispatch()

    cursor = db_instance.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name='users';
        """
    )

    assert list(cursor.fetchall()) == []


def test_rollback_migration(initialized_project, db_instance):
    project_path, versions_dir = initialized_project

    cmd = Commands(CommandsEnum.GENERATE)

    # Create migrations
    cmd.dispatch(migration_name="create_users_table")
    cmd.dispatch(migration_name="add_age_to_users")

    generated_files = sorted(versions_dir.glob("*.sql"))
    assert len(generated_files) == 2

    # First migration
    generated_files[0].write_text(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL
        );
        """,
        encoding="utf-8",
    )

    # Second migration
    generated_files[1].write_text(
        """
        -- Up migration
        ALTER TABLE users ADD COLUMN age INT;
        -- Down migration
        ALTER TABLE users DROP COLUMN age;
        """
    )

    # Apply upgrades
    cmd = Commands(CommandsEnum.UPGRADE)
    cmd.dispatch()

    cursor = db_instance.execute("SELECT age FROM users")
    assert cursor is not None
    cursor.close()

    # Downgrade last migration
    cmd = Commands(CommandsEnum.ROLLBACK)
    cmd.dispatch(migrations_to_rollback=1)

    cursor = db_instance.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='users' AND column_name='age';
        """
    )

    assert list(cursor.fetchall()) == []
