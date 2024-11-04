from pydantic_settings import BaseSettings


class DBSettings(BaseSettings):
    """Databases settings"""

    DB_URL: str
    TESTS_DB_URL: str
    REDIS_URL: str


settings = DBSettings()
