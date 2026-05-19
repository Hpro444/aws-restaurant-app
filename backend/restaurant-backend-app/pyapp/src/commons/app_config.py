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

    # DynamoDB table aliases (resolved to full names at runtime)
    login_attempts_table: str = "login-attempts"
    waiters_table: str = "waiters"
    customers_table: str = "customers"
    locations_table: str = "locations"
    tables_table: str = "tables"
    dishes_table: str = "dishes"
    shifts_table: str = "shifts"
    slots_table: str = "slots"
    reservations_table: str = "reservations"
    feedback_culinary_table: str = "feedback-culinary"
    feedback_service_table: str = "feedback-service"
    waiter_emails_table: str = "waiter-emails"
    admins_table: str = "admins"
    admin_emails_table: str = "admin-emails"

    # Login attempt tracking
    max_login_attempts: int = 5
    lockout_seconds: int = 900

    model_config = SettingsConfigDict(
        extra="ignore",
        env_file=".env",
        env_parse_enums=True,
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
        case_sensitive=False,
    )
