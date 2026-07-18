from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    # POSTGRES_USER : str
    # weather_api_key: str
    # log_level: str = "info"
    pass


settings = Settings()
