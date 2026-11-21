import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["NAGARLENS_DATABASE_URL"] = "sqlite:///" + str(Path(os.environ.get("TMPDIR", "/tmp")) / "nagarlens_test.db")
os.environ["NAGARLENS_DISABLE_LIVE_CLAUDE"] = "1"
db = Path(os.environ["NAGARLENS_DATABASE_URL"].replace("sqlite:///", ""))
if db.exists():
    db.unlink()
