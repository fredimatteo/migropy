import sys
from dataclasses import dataclass

import psycopg

from migratron.core.logger import logger
from migratron.databases.db_connector import DatabaseConnector


@dataclass
class Config:
    host: str
    port: str | int
    user: str
    password: str
    database: str

    def __post_init__(self):
        if isinstance(self.port, str):
            self.port = int(self.port)



class Postgres(DatabaseConnector):
    def __init__(self, config: Config):
        self.host = config.host
        self.user = config.user
        self.password = config.password
        self.database = config.database
        self.conn: psycopg.Connection | None = None

    def connection(self):
        self.conn = self._create_connection()

    def __get_private_password(self) -> str:
        private_pwd: str = '*' * len(self.password)
        return private_pwd or '*'

    def _create_connection(self):
        try:
            logger.debug('creating connection to psql host: %s port: %s user: %s password: %s dbname: %s',
                         self.host,
                         self.port,
                         self.user,
                         self.__get_private_password(),
                         self.database)
            connection_instance = psycopg.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.database
            )
            logger.debug('connection created')
            return connection_instance
        except psycopg.Error as e:
            logger.error("error while connecting to database: %s", e)
            sys.exit(1)

    def commit(self):
        if self.conn:
            self.conn.commit()

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    def execute(self, query):
        if not self.conn:
            self.conn = self._create_connection()

        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
        except psycopg.Error as e:
            logger.error("error while executing query: %s", e)
            self.rollback()
            sys.exit(1)

    def __del__(self):
        if self.conn:
            self.conn.close()
            logger.debug('connection closed')