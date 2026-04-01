from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "finance_dashboard.db"

ROLE_VIEWER = "viewer"
ROLE_ANALYST = "analyst"
ROLE_ADMIN = "admin"
VALID_ROLES = {ROLE_VIEWER, ROLE_ANALYST, ROLE_ADMIN}

STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"
VALID_STATUSES = {STATUS_ACTIVE, STATUS_INACTIVE}
