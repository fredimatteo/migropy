# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)

## [0.4.0] - 2025-11-13

### Added

- Possibility to define custom migration scripts directory's name.
- Support for environment variables in database connection's details.

### Changed

- Update dependencies to latest versions.
- Improve error handling for database connections.
- Refactor migration engine for better performance.

### Changed

- Code refactor to improve readability and maintainability.

## [0.3.1] - 2025-07-15

### Changed

- Code refactor to improve readability and maintainability.

## [0.3.0] - 2025-04-14

### Added

- Rollback command to revert the last n applied migration.

## [0.2.2] - 2025-03-28

### Changed

- Refactor CLI commands to use a single command class.
- Refactor MigrationEngine to allow usage from python code.

## [0.2.1] - 2025-03-24

### Changed

- Increase python version to 3.10.
- Make MigrationEngine.list_revisions static.

## [0.2.0] - 2025-03-24

### Added

- MySQL database support.

## [0.1.1] - 2025-03-20

### Added

- Initial project setup.
- PostgreSQL database support.