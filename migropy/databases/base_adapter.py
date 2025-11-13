from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeAlias, Union

import mysql.connector
import psycopg

DbConnection: TypeAlias = Union[
    psycopg.Connection,
    mysql.connector.connection.MySQLConnection
]


class BaseAdapter(ABC):
    @abstractmethod
    def execute(self, query):
        pass

    @abstractmethod
    def commit(self):
        pass

    @abstractmethod
    def rollback(self):
        pass