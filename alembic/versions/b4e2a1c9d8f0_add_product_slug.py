"""add_product_slug

Revision ID: b4e2a1c9d8f0
Revises: 01d5189d3343
Create Date: 2026-04-07 04:30:00.000000

"""
import re
from alembic import op
import sqlalchemy as sa


revision = 'b4e2a1c9d8f0'
down_revision = '01d5189d3343'
branch_labels = None
depends_on = None


def _slugify(text: str) -> str:
    if not text:
        return ""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower())
    s = s.strip("-")
    s = re.sub(r"-+", "-", s)
    return s[:200]


def upgrade() -> None:
    # Add the slug column (nullable initially so backfill works)
    op.add_column('products', sa.Column('slug', sa.String(), nullable=True))

    # Backfill: generate unique slugs for all existing products
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, name FROM products ORDER BY id")).fetchall()

    used_slugs = set()
    for row in rows:
        pid = row[0]
        name = row[1] or "product"
        base = _slugify(name) or "product"
        slug = base
        n = 2
        while slug in used_slugs:
            slug = f"{base}-{n}"
            n += 1
        used_slugs.add(slug)
        conn.execute(
            sa.text("UPDATE products SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": pid},
        )

    # Now create unique index
    op.create_index('ix_products_slug', 'products', ['slug'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_products_slug', table_name='products')
    op.drop_column('products', 'slug')
