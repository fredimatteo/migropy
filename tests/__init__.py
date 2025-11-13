import os

from dotenv import load_dotenv

load_dotenv()

DB_NAME: str = os.getenv("POSTGRES_DB", "")
DB_USER: str = os.getenv("POSTGRES_USER", "")
DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
DB_HOST: str = os.getenv("DB_HOST", "localhost")
DB_PORT: int = int(os.getenv("DB_PORT", "5432"))

print(DB_NAME)


__all__ = [
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "DB_HOST",
    "DB_PORT",
]
