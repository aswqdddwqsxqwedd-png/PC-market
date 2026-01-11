"""Add SUPPORT role and order_id to messages

Revision ID: 0202e642d068
Revises: 80efb544a961
Create Date: 2026-01-09 04:51:10.168442

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0202e642d068'
down_revision = '80efb544a961'
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
    
    # Check if order_id column already exists (for SQLite compatibility)
    columns = [col['name'] for col in inspector.get_columns('messages')]
    
    # Add order_id column if it doesn't exist
    if 'order_id' not in columns:
        with op.batch_alter_table('messages', schema=None) as batch_op:
            batch_op.add_column(sa.Column('order_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_messages_order_id', 'orders', ['order_id'], ['id'])
    
    # Note: UserRole enum change will be handled automatically by SQLAlchemy
    # SQLite doesn't support ALTER for enum types, so this is handled at application level


def downgrade() -> None:
    # Check if table exists before checking columns
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Get list of tables
    tables = inspector.get_table_names()
    
    # Only proceed if messages table exists
    if 'messages' not in tables:
        return
    
    # Check if order_id column exists before dropping
    columns = [col['name'] for col in inspector.get_columns('messages')]
    
    if 'order_id' in columns:
        with op.batch_alter_table('messages', schema=None) as batch_op:
            batch_op.drop_constraint('fk_messages_order_id', type_='foreignkey')
            batch_op.drop_column('order_id')
