"""Compliance alerts migration

Revision ID: 002_compliance_alerts
Revises: 001_initial
Create Date: 2026-06-30 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_compliance_alerts'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create new enum types
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'compliance_scope_type') THEN
                CREATE TYPE compliance_scope_type AS ENUM ('1', '2', '3', 'total');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_type_enum') THEN
                CREATE TYPE alert_type_enum AS ENUM (
                    'emission_spike', 'threshold_exceeded', 'low_sustainability_score'
                );
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_severity_enum') THEN
                CREATE TYPE alert_severity_enum AS ENUM ('low', 'medium', 'high', 'critical');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'alert_status_enum') THEN
                CREATE TYPE alert_status_enum AS ENUM ('active', 'acknowledged', 'resolved');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'report_type_enum') THEN
                CREATE TYPE report_type_enum AS ENUM ('sustainability', 'compliance');
            END IF;
        END
        $$;
    """)

    # 2. Alter organizations table
    op.execute("""
        ALTER TABLE organizations
            ADD COLUMN IF NOT EXISTS baseline_year INTEGER,
            ADD COLUMN IF NOT EXISTS target_reduction_pct FLOAT NOT NULL DEFAULT 20.0,
            ADD COLUMN IF NOT EXISTS net_zero_target_year INTEGER;
    """)

    # 3. Alter reports table - add report_type
    op.execute("""
        ALTER TABLE reports
            ADD COLUMN IF NOT EXISTS report_type report_type_enum NOT NULL DEFAULT 'sustainability';
    """)

    # 4. Create compliance_thresholds table
    op.create_table(
        'compliance_thresholds',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column(
            'scope',
            postgresql.ENUM('1', '2', '3', 'total', name='compliance_scope_type', create_type=False),
            nullable=False
        ),
        sa.Column('threshold_tco2e', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint('threshold_tco2e > 0', name='check_threshold_positive'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'scope', name='uq_compliance_threshold_org_scope'),
    )

    # 5. Create alerts table
    op.create_table(
        'alerts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column(
            'alert_type',
            postgresql.ENUM(
                'emission_spike', 'threshold_exceeded', 'low_sustainability_score',
                name='alert_type_enum', create_type=False
            ),
            nullable=False
        ),
        sa.Column(
            'severity',
            postgresql.ENUM('low', 'medium', 'high', 'critical', name='alert_severity_enum', create_type=False),
            nullable=False
        ),
        sa.Column(
            'status',
            postgresql.ENUM('active', 'acknowledged', 'resolved', name='alert_status_enum', create_type=False),
            server_default='active',
            nullable=False
        ),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column(
            'scope',
            postgresql.ENUM('1', '2', '3', 'total', name='compliance_scope_type', create_type=False),
            nullable=True
        ),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('period_month', sa.Date(), nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # 6. Enable RLS on new tables
    for table in ['compliance_thresholds', 'alerts']:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")

    # 7. Create RLS policies (same pattern as 001_initial.py)
    for table in ['compliance_thresholds', 'alerts']:
        op.execute(f"""
            CREATE POLICY {table}_rls_policy ON {table}
            FOR ALL TO authenticated
            USING (org_id = get_user_org_id())
            WITH CHECK (org_id = get_user_org_id());
        """)


def downgrade() -> None:
    # Drop policies
    for table in ['compliance_thresholds', 'alerts']:
        op.execute(f"DROP POLICY IF EXISTS {table}_rls_policy ON {table}")

    # Disable RLS
    for table in ['compliance_thresholds', 'alerts']:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    # Drop new tables
    op.drop_table('alerts')
    op.drop_table('compliance_thresholds')

    # Revert reports table
    op.execute("ALTER TABLE reports DROP COLUMN IF EXISTS report_type;")

    # Revert organizations table
    op.execute("""
        ALTER TABLE organizations
            DROP COLUMN IF EXISTS baseline_year,
            DROP COLUMN IF EXISTS target_reduction_pct,
            DROP COLUMN IF EXISTS net_zero_target_year;
    """)

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS report_type_enum")
    op.execute("DROP TYPE IF EXISTS alert_status_enum")
    op.execute("DROP TYPE IF EXISTS alert_severity_enum")
    op.execute("DROP TYPE IF EXISTS alert_type_enum")
    op.execute("DROP TYPE IF EXISTS compliance_scope_type")
