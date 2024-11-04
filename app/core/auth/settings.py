from pydantic_settings import BaseSettings


class AuthSettings(BaseSettings):
    ACCESS_SECRET: str
    REFRESH_SECRET: str
    COOKIE_DOMAIN: str
    RESTORE_PASSWORD_SECRET: str
    VERIFICATION_SECRET: str
    ACCESS_LIFETIME: int = 600
    REFRESH_LIFETIME: int = 2592000
    REDIS_UID_TO_REF_CODE_RPEFIX: str
    REDIS_REF_CODE_TO_UID_RPEFIX: str

    OAUTH_GOOGLE_CLIENT_ID: str
    OAUTH_GOOGLE_CLIENT_SECRET: str
    OAUTH_GOOGLE_SECRET: str

    OAUTH_GITHUB_CLIENT_ID: str
    OAUTH_GITHUB_CLIENT_SECRET: str
    OAUTH_GITHUB_SECRET: str


settings = AuthSettings()
