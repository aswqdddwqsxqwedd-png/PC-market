"""add_database_indexes_for_performance

Revision ID: b58417304312
Revises: d5bdff73004e
Create Date: 2026-01-09 09:47:51.562978

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b58417304312'
down_revision = 'd5bdff73004e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check which tables exist before creating indexes
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Indexes for items table
    if 'items' in tables:
        op.create_index('idx_items_category_id', 'items', ['category_id'])
        op.create_index('idx_items_owner_id', 'items', ['owner_id'])
        op.create_index('idx_items_price', 'items', ['price'])
        op.create_index('idx_items_is_active', 'items', ['is_active'])
        op.create_index('idx_items_created_at', 'items', ['created_at'])
        # Composite index for common queries (category + active status)
        op.create_index('idx_items_category_active', 'items', ['category_id', 'is_active'])
    
    # Indexes for orders table
    if 'orders' in tables:
        op.create_index('idx_orders_user_id', 'orders', ['user_id'])
        op.create_index('idx_orders_status', 'orders', ['status'])
        op.create_index('idx_orders_created_at', 'orders', ['created_at'])
        # Composite index for user orders with status
        op.create_index('idx_orders_user_status', 'orders', ['user_id', 'status'])
    
    # Indexes for order_items table
    if 'order_items' in tables:
        op.create_index('idx_order_items_order_id', 'order_items', ['order_id'])
        op.create_index('idx_order_items_item_id', 'order_items', ['item_id'])
    
    # Indexes for cart_items table
    if 'cart_items' in tables:
        op.create_index('idx_cart_items_user_id', 'cart_items', ['user_id'])
        op.create_index('idx_cart_items_item_id', 'cart_items', ['item_id'])
        op.create_index('idx_cart_items_user_item', 'cart_items', ['user_id', 'item_id'], unique=True)
    
    # Indexes for messages table
    if 'messages' in tables:
        op.create_index('idx_messages_sender_id', 'messages', ['sender_id'])
        op.create_index('idx_messages_receiver_id', 'messages', ['receiver_id'])
        op.create_index('idx_messages_order_id', 'messages', ['order_id'])
        op.create_index('idx_messages_created_at', 'messages', ['created_at'])
        op.create_index('idx_messages_is_read', 'messages', ['is_read'])
        op.create_index('idx_messages_is_resolved', 'messages', ['is_resolved'])
        # Composite index for conversation queries
        op.create_index('idx_messages_sender_receiver', 'messages', ['sender_id', 'receiver_id'])
        op.create_index('idx_messages_receiver_read', 'messages', ['receiver_id', 'is_read'])
    
    # Indexes for users table
    if 'users' in tables:
        op.create_index('idx_users_role', 'users', ['role'])
        op.create_index('idx_users_is_active', 'users', ['is_active'])
        op.create_index('idx_users_created_at', 'users', ['created_at'])


def downgrade() -> None:
    # Check which tables exist before dropping indexes
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    
    # Drop indexes in reverse order, only if tables exist
    if 'users' in tables:
        try:
            op.drop_index('idx_users_created_at', 'users')
        except:
            pass
        try:
            op.drop_index('idx_users_is_active', 'users')
        except:
            pass
        try:
            op.drop_index('idx_users_role', 'users')
        except:
            pass
    
    if 'messages' in tables:
        try:
            op.drop_index('idx_messages_receiver_read', 'messages')
        except:
            pass
        try:
            op.drop_index('idx_messages_sender_receiver', 'messages')
        except:
            pass
        try:
            op.drop_index('idx_messages_is_resolved', 'messages')
        except:
            pass
        try:
            op.drop_index('idx_messages_is_read', 'messages')
        except:
            pass
        try:
            op.drop_index('idx_messages_created_at', 'messages')
        except:
            pass
        try:
            op.drop_index('idx_messages_order_id', 'messages')
        except:
            pass
        try:
            op.drop_index('idx_messages_receiver_id', 'messages')
        except:
            pass
        try:
            op.drop_index('idx_messages_sender_id', 'messages')
        except:
            pass
    
    if 'cart_items' in tables:
        try:
            op.drop_index('idx_cart_items_user_item', 'cart_items')
        except:
            pass
        try:
            op.drop_index('idx_cart_items_item_id', 'cart_items')
        except:
            pass
        try:
            op.drop_index('idx_cart_items_user_id', 'cart_items')
        except:
            pass
    
    if 'order_items' in tables:
        try:
            op.drop_index('idx_order_items_item_id', 'order_items')
        except:
            pass
        try:
            op.drop_index('idx_order_items_order_id', 'order_items')
        except:
            pass
    
    if 'orders' in tables:
        try:
            op.drop_index('idx_orders_user_status', 'orders')
        except:
            pass
        try:
            op.drop_index('idx_orders_created_at', 'orders')
        except:
            pass
        try:
            op.drop_index('idx_orders_status', 'orders')
        except:
            pass
        try:
            op.drop_index('idx_orders_user_id', 'orders')
        except:
            pass
    
    if 'items' in tables:
        try:
            op.drop_index('idx_items_category_active', 'items')
        except:
            pass
        try:
            op.drop_index('idx_items_created_at', 'items')
        except:
            pass
        try:
            op.drop_index('idx_items_is_active', 'items')
        except:
            pass
        try:
            op.drop_index('idx_items_price', 'items')
        except:
            pass
        try:
            op.drop_index('idx_items_owner_id', 'items')
        except:
            pass
        try:
            op.drop_index('idx_items_category_id', 'items')
        except:
            pass
