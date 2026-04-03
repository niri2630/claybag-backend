"""add_reviews_table_and_category_icon

Revision ID: 61392849f386
Revises: 9584302d58e5
Create Date: 2026-04-03 19:53:42.430654

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


revision = '61392849f386'
down_revision = '9584302d58e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa_inspect(conn)
    existing_tables = inspector.get_table_names()

    # Create reviews table if it doesn't exist
    if 'reviews' not in existing_tables:
        op.create_table(
            'reviews',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False),
            sa.Column('rating', sa.Integer(), nullable=False),
            sa.Column('comment', sa.Text(), nullable=True),
            sa.Column('is_approved', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index('ix_reviews_id', 'reviews', ['id'])

    # Add icon column to categories if it doesn't exist
    existing_columns = [col['name'] for col in inspector.get_columns('categories')]
    if 'icon' not in existing_columns:
        op.add_column('categories', sa.Column('icon', sa.String(), server_default='category', nullable=False))


def downgrade() -> None:
    op.drop_column('categories', 'icon')
    op.drop_index('ix_reviews_id', table_name='reviews')
    op.drop_table('reviews')
