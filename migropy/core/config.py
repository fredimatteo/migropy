from dataclasses import dataclass


@dataclass
class Config:
    """
    Configuration class for the application.
    """
    db_host: str = 'localhost'
    db_port: int = 0
    db_user: str = ''
    db_password: str = ''
    db_name: str = ''
    db_type: str = ''

    script_location: str = 'migropy'
    base_schema: str = 'public'

    logger_level: str = 'INFO'


default_config = Config()
