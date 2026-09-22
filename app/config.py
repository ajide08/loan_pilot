from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATBASE_URL: str
    SECRET_KEY: str

    JWT_ALGORITHM: str = 'HS256'
    ACCES_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

settings = Settings()