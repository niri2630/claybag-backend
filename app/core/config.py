from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/claybag"
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    UPLOAD_DIR: str = "uploads"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # S3 (set in production env to use S3, leave empty for local disk)
    S3_BUCKET: str = ""
    S3_REGION: str = "ap-south-1"
    S3_PUBLIC_URL: str = ""  # e.g. https://claybag-media-prod.s3.ap-south-1.amazonaws.com

    # Cashfree Payment Gateway
    CASHFREE_APP_ID: str = ""
    CASHFREE_SECRET_KEY: str = ""
    CASHFREE_ENV: str = "sandbox"  # "sandbox" or "production"
    FRONTEND_URL: str = "http://localhost:3000"

    # Email / SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""  # display "From" email (defaults to SMTP_USER)
    SMTP_TLS: bool = True

    # GST / Tax compliance
    COMPANY_STATE: str = "Karnataka"  # Registered business state — used for intra/inter state GST split
    COMPANY_GSTIN: str = ""  # Company GST identification number (shown on invoices)
    COMPANY_LEGAL_NAME: str = "ClayBag"
    DEFAULT_GST_RATE: float = 18.0  # Default GST % for products without explicit rate

    @property
    def origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"


settings = Settings()
