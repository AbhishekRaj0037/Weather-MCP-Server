from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    DATABASE_URL: str = SettingsConfigDict(env_file=".env")
    Gemini_API_Key: str = SettingsConfigDict(env_file=".env")
    POSTGRES_DB: str = SettingsConfigDict(env_file=".env")
    POSTGRES_PASSWORD: str = SettingsConfigDict(env_file=".env")
    POSTGRES_USER: str = SettingsConfigDict(env_file=".env")
    SECRET_KEY: str = "77eGSyhinlNSVTLZKJ/qYqktRaGuM5SyQmTBqJ6AOZM="
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEBUG: bool = False
    ENVIRONMENT: str = "local"


settings = Settings()
