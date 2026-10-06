from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://contrib:contrib@127.0.0.1:5433/contrib"
    allowed_repo_roots: str = ""  # comma-separated absolute dirs; empty = any local path
    batch_size: int = 500

    @property
    def allowed_roots(self) -> list[Path]:
        return [Path(p).resolve() for p in self.allowed_repo_roots.split(",") if p.strip()]


settings = Settings()
