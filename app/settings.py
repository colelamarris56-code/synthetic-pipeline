"""
Central configuration handling for the Clinic Synthesizer Operator.
Manages environment variables and application settings.
"""
from typing import Optional
import os
from dataclasses import dataclass

@dataclass
class Config:
    # Database settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "clinic_synth")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASS: str = os.getenv("DB_PASS", "")
    
    # API endpoints
    BILLING_API_URL: str = os.getenv("BILLING_API_URL", "http://localhost:8001")
    REVIEW_API_URL: str = os.getenv("REVIEW_API_URL", "http://localhost:8002")
    
    # API timeouts (seconds)
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))
    
    # Streamlit configuration
    STREAMLIT_THEME: Optional[str] = os.getenv("STREAMLIT_THEME")
    
    @property
    def db_url(self) -> str:
        """Get the database URL in the format required by psycopg."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# Global configuration instance
config = Config()