"""Initial schema: organizations, repositories, reviews

Revision ID: ee1dff35efb4
Revises: 
Create Date: 2026-06-01 19:29:40.121880

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === organizations ===
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('installation_id', sa.Integer(), unique=True, nullable=False, index=True),
        sa.Column('github_login', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # === repositories ===
    op.create_table(
        'repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('github_id', sa.Integer(), unique=True, nullable=False),
        sa.Column('full_name', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('is_private', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # === reviews ===
    op.create_table(
        'reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False, index=True),
        sa.Column('repo_full_name', sa.String(255), nullable=False, index=True),
        sa.Column('pr_number', sa.Integer(), nullable=False),
        sa.Column('commit_sha', sa.String(40), nullable=False),
        sa.Column('status', sa.String(50), default='pending', nullable=False),
        sa.Column('problems_count', sa.Integer(), default=0, nullable=False),
        sa.Column('problems_data', postgresql.JSON, nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('reviews')
    op.drop_table('repositories')
    op.drop_table('organizations')