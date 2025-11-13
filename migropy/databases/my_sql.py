import sys

import mysql.connector

from migropy.core.logger import logger
from migropy.databases.base_adapter import BaseAdapter
from migropy.databases.commons import DbConfig


class MySql(BaseAdapter):
    def __init__(self, config: DbConfig):
        self.host = config.host
        self.user = config.user
        self.port = config.port
        self.password = config.password
        self.database = config.database
        self.conn: mysql.connector.connection.MySQLConnection | None = None

    def __create_connection(self):
        try:
            connection_instance = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            return connection_instance
        except mysql.connector.Error as e:
            logger.error('error while connecting to database: %s', e)
            sys.exit(1)

    def commit(self):
        if self.conn:
            self.conn.commit()

    def execute(self, query):
        if not self.conn:
            self.__create_connection()

        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            return cursor
        except mysql.connector.Error as e:
            logger.error('error while executing query: %s', e)
            self.rollback()
            sys.exit(1)

    def rollback(self):
        if self.conn:
            self.conn.rollback()

    def __del__(self):
        if self.conn:
            self.conn.close()
            logger.debug('connection closed')
