"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-06-13 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create enum types first (conditionally)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'plan_type') THEN
                CREATE TYPE plan_type AS ENUM ('free', 'pro', 'enterprise');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'role_type') THEN
                CREATE TYPE role_type AS ENUM ('admin', 'analyst', 'viewer');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'scope_type') THEN
                CREATE TYPE scope_type AS ENUM ('1', '2', '3');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transport_mode_type') THEN
                CREATE TYPE transport_mode_type AS ENUM ('air', 'sea', 'road', 'rail');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'report_status_type') THEN
                CREATE TYPE report_status_type AS ENUM ('pending', 'processing', 'done', 'failed');
            END IF;
        END
        $$;
    """)

    # 2. Create tables
    # Organizations Table
    op.create_table(
        'organizations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('country', sa.CHAR(length=2), nullable=True),
        sa.Column('plan', postgresql.ENUM('free', 'pro', 'enterprise', name='plan_type', create_type=False), server_default='free', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('admin', 'analyst', 'viewer', name='role_type', create_type=False), server_default='analyst', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Suppliers Table
    op.create_table(
        'suppliers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('country', sa.CHAR(length=2), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('emission_factor_kg_per_unit', sa.Float(), server_default='1.0', nullable=True),
        sa.Column('esg_score', sa.Float(), nullable=True),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint('esg_score >= 0 AND esg_score <= 100', name='check_esg_score_range'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Emission Records Table
    op.create_table(
        'emission_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=True),
        sa.Column('scope', postgresql.ENUM('1', '2', '3', name='scope_type', create_type=False), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('amount_tco2e', sa.Float(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('source', sa.String(length=100), server_default='manual', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint('amount_tco2e >= 0', name='check_amount_tco2e_positive'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Supply Chain Edges Table
    op.create_table(
        'supply_chain_edges',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('from_supplier_id', sa.UUID(), nullable=False),
        sa.Column('to_supplier_id', sa.UUID(), nullable=False),
        sa.Column('transport_mode', postgresql.ENUM('air', 'sea', 'road', 'rail', name='transport_mode_type', create_type=False), nullable=False),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('weight_tonnes', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Reports Table
    op.create_table(
        'reports',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('generated_by', sa.UUID(), nullable=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('s3_url', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'processing', 'done', 'failed', name='report_status_type', create_type=False), server_default='pending', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['generated_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # AI Conversations Table
    op.create_table(
        'ai_conversations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('messages', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create RLS Helper Function to prevent infinite recursion
    op.execute("""
        CREATE OR REPLACE FUNCTION get_user_org_id()
        RETURNS UUID AS $$
            SELECT org_id FROM users WHERE id = auth.uid();
        $$ LANGUAGE sql SECURITY DEFINER;
    """)

    # 4. Enable Row Level Security (RLS) on all tables except organizations
    tables_to_rls = ['users', 'suppliers', 'emission_records', 'supply_chain_edges', 'reports', 'ai_conversations']
    for table in tables_to_rls:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")

    # 5. Create Policies mapping: org_id = (SELECT org_id FROM users WHERE id = auth.uid()) via our helper function
    # Note: For users table we allow user to read/write their own row or matching org_id rows.
    op.execute("""
        CREATE POLICY users_rls_policy ON users
        FOR ALL TO authenticated
        USING (id = auth.uid() OR org_id = get_user_org_id())
        WITH CHECK (id = auth.uid() OR org_id = get_user_org_id());
    """)

    other_tables = ['suppliers', 'emission_records', 'supply_chain_edges', 'reports', 'ai_conversations']
    for table in other_tables:
        op.execute(f"""
            CREATE POLICY {table}_rls_policy ON {table}
            FOR ALL TO authenticated
            USING (org_id = get_user_org_id())
            WITH CHECK (org_id = get_user_org_id());
        """)


def downgrade() -> None:
    # Drop policies
    other_tables = ['suppliers', 'emission_records', 'supply_chain_edges', 'reports', 'ai_conversations']
    for table in other_tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_rls_policy ON {table}")
    op.execute("DROP POLICY IF EXISTS users_rls_policy ON users")

    # Disable RLS
    tables_to_rls = ['users', 'suppliers', 'emission_records', 'supply_chain_edges', 'reports', 'ai_conversations']
    for table in tables_to_rls:
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    # Drop helper function
    op.execute("DROP FUNCTION IF EXISTS get_user_org_id();")

    # Drop tables
    op.drop_table('ai_conversations')
    op.drop_table('reports')
    op.drop_table('supply_chain_edges')
    op.drop_table('emission_records')
    op.drop_table('suppliers')
    op.drop_table('users')
    op.drop_table('organizations')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS report_status_type")
    op.execute("DROP TYPE IF EXISTS transport_mode_type")
    op.execute("DROP TYPE IF EXISTS scope_type")
    op.execute("DROP TYPE IF EXISTS role_type")
    op.execute("DROP TYPE IF EXISTS plan_type")
