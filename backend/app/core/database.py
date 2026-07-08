from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def ensure_performance_schema():
    # create_all() ne modifie pas les tables existantes. Ces DDL idempotents
    # garantissent les colonnes/index requis sans casser les environnements deja crees.
    statements = [
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS address VARCHAR",
        "CREATE INDEX IF NOT EXISTS ix_alerts_user_id ON alerts (user_id)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_created_at ON alerts (created_at)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_status ON alerts (status)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_severity ON alerts (severity)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_assigned_to ON alerts (assigned_to)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_status_created_at ON alerts (status, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_user_id_created_at ON alerts (user_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_location_gist ON alerts USING GIST (location)",
        "CREATE INDEX IF NOT EXISTS ix_alerts_location_geography_gist ON alerts USING GIST ((location::geography))",
        "CREATE INDEX IF NOT EXISTS ix_location_updates_alert_id ON location_updates (alert_id)",
        "CREATE INDEX IF NOT EXISTS ix_location_updates_alert_id_created_at ON location_updates (alert_id, created_at)",
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
