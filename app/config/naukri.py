from pydantic_settings import BaseSettings, SettingsConfigDict


class NaukriSettings(BaseSettings):

    username: str
    password: str

    model_config = SettingsConfigDict(
        env_prefix="NAUKRI_",
        env_file=".env",
        extra="ignore",
    )