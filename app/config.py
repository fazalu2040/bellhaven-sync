import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    crm_base_url: str = os.getenv("CRM_BASE_URL", "https://analyst-assessment-production.up.railway.app/api/v1")
    crm_token: str = os.getenv("CRM_TOKEN", "bh_WsQVC6cELIvk1PojUEnRBQ")
    bellhaven_base_url: str = os.getenv("BELLHAVEN_BASE_URL", "https://analyst-assessment-production.up.railway.app")
    db_path: str = os.getenv("APP_DB_PATH", str(Path(__file__).resolve().parent.parent / "data" / "bellhaven_sync.db"))
    app_name: str = os.getenv("APP_NAME", "bellhaven-sync")

    @property
    def accounts_url(self) -> str:
        return f"{self.crm_base_url.rstrip('/')}/accounts"


settings = Settings()
