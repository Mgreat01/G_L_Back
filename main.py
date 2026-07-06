from pathlib import Path
import sys


backend_path = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app
