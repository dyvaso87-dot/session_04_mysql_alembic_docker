"""crear tabla productos

Revision ID: 0001_crear_tabla_productos
Revises:
Create Date: 2026-09-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_crear_tabla_productos"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "productos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("precio", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_productos_id"), "productos", ["id"], unique=False)
    op.create_index(op.f("ix_productos_nombre"), "productos", ["nombre"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_productos_nombre"), table_name="productos")
    op.drop_index(op.f("ix_productos_id"), table_name="productos")
    op.drop_table("productos")
