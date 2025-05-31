import os
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    spotify_client_id: str
    spotify_client_secret: str
    spotify_api_base_url: str

    # Pass env_file at instantiation so the class-level default is disabled
    model_config = SettingsConfigDict(env_file=None)


def get_settings(env_profile: Optional[str] = None) -> Settings:
    """
    Load settings from
        1) .env.{env_profile} if it exists
        2) .env               if it exists
    The profile defaults to the ENV_PROFILE environment variable (or 'dev').
    """
    if env_profile is None:
        env_profile = os.getenv("ENV_PROFILE", "dev")

    cwd = os.getcwd()
    candidate_files: List[str] = [
        os.path.join(cwd, f".env.{env_profile}"),
        os.path.join(cwd, ".env"),
    ]
    env_files = [f for f in candidate_files if os.path.isfile(f)]

    return Settings(_env_file=env_files or None)
