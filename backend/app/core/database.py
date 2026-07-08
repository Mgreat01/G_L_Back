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
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS encryption_algorithm VARCHAR NOT NULL DEFAULT 'AES-256-GCM'",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS encrypted_content_nonce VARCHAR",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS encrypted_content_tag VARCHAR",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS key_encryption_algorithm VARCHAR NOT NULL DEFAULT 'RSA-OAEP-SHA256'",
        "ALTER TABLE alerts ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP WITH TIME ZONE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS public_key_algorithm VARCHAR",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL",
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
        "CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)",
        "CREATE INDEX IF NOT EXISTS ix_users_is_active ON users (is_active)",
        "CREATE INDEX IF NOT EXISTS ix_users_email_verified ON users (email_verified)",
        "CREATE INDEX IF NOT EXISTS ix_alert_history_alert_id ON alert_history (alert_id)",
        "CREATE INDEX IF NOT EXISTS ix_alert_history_created_at ON alert_history (created_at)",
        "CREATE INDEX IF NOT EXISTS ix_alert_recipient_keys_alert_id ON alert_recipient_keys (alert_id)",
        "CREATE INDEX IF NOT EXISTS ix_alert_recipient_keys_recipient_user_id ON alert_recipient_keys (recipient_user_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_alert_recipient_keys_alert_recipient ON alert_recipient_keys (alert_id, recipient_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_notifications_user_read_created ON notifications (user_id, read, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_audit_logs_resource ON audit_logs (resource_type, resource_id)",
        "CREATE INDEX IF NOT EXISTS ix_rescue_team_locations_user_created_at ON rescue_team_locations (user_id, created_at)",
        "CREATE INDEX IF NOT EXISTS ix_rescue_team_locations_location_gist ON rescue_team_locations USING GIST (location)",
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
