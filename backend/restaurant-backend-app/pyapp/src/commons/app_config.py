"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Central settings class; each field maps to an uppercase environment variable.

    Example env vars: USER_POOL_NAME, AWS_REGION.
    """

    # Cognito
    user_pool_name: str = "restaurant-userpool"
    aws_region: str = "eu-west-3"
    cognito_max_results: int = 60

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_parse_enums=True,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
        case_sensitive=False,
    )
