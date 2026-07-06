import os
from pathlib import Path

from dotenv import load_dotenv


backend_dir = Path(__file__).resolve().parents[2]
project_root = backend_dir.parent

load_dotenv(project_root / ".env")
load_dotenv(backend_dir / ".env", override=True)

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL")

settings = Settings()
