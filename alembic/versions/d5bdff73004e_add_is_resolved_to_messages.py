"""add_is_resolved_to_messages

Revision ID: d5bdff73004e
Revises: 0202e642d068
Create Date: 2026-01-09 06:05:14.770677

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5bdff73004e'
down_revision = '0202e642d068'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table exists before checking columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get list of tables
    tables = inspector.get_table_names()
    
    # Only proceed if messages table exists
    if 'messages' not in tables:
        # Table doesn't exist yet, skip this migration
        # It will be created by init_db() or a later migration
        return
    
    # Check if column already exists
    columns = [col['name'] for col in inspector.get_columns('messages')]
    
    if 'is_resolved' not in columns:
        # Use batch mode for SQLite
        with op.batch_alter_table('messages', schema=None) as batch_op:
            batch_op.add_column(sa.Column('is_resolved', sa.Boolean(), nullable=True, server_default='0'))


def downgrade() -> None:
    # Check if table exists before dropping column
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get list of tables
    tables = inspector.get_table_names()
    
    # Only proceed if messages table exists
    if 'messages' not in tables:
        return
    
    columns = [col['name'] for col in inspector.get_columns('messages')]
    
    if 'is_resolved' in columns:
        with op.batch_alter_table('messages', schema=None) as batch_op:
            batch_op.drop_column('is_resolved')
