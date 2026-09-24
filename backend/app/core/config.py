from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = "postgresql://notebuddy:notebuddy@localhost:5432/notebuddy"

    # AWS
    aws_region: str = "us-east-1"
    s3_bucket_name: str = ""
    sqs_queue_url: str = ""

    # Cognito
    cognito_user_pool_id: str = ""
    cognito_client_id: str = ""
    cognito_region: str = ""  # falls back to aws_region if empty

    # OpenAI
    openai_api_key: str = ""

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cognito_region_resolved(self) -> str:
        return self.cognito_region or self.aws_region

    @property
    def cognito_issuer(self) -> str:
        return f"https://cognito-idp.{self.cognito_region_resolved}.amazonaws.com/{self.cognito_user_pool_id}"

    @property
    def cognito_jwks_url(self) -> str:
        return f"{self.cognito_issuer}/.well-known/jwks.json"


settings = Settings()
