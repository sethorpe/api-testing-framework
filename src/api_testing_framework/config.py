
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    spotify_client_id: str
    spotify_client_secret: str
    spotify_api_base_url: str

    model_config = SettingsConfigDict(env_file=".env")

def get_settings() -> Settings:
    """
    Read and return a fresh Settings object.
    """
    return Settings()