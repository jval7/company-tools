import pydantic_settings


class Configs(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8"
    )
    # aws
    aws_access_key_id: str
    aws_secret_access_key: str
    time_to_sync: int
    time_to_clean: int


configs = Configs()
