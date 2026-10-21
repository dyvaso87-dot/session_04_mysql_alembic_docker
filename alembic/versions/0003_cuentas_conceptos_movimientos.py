"""crear cuentas, conceptos y movimientos financieros

Revision ID: 0003_financial_modules
Revises: 0002_empresas_usuarios
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_financial_modules"
down_revision = "0002_empresas_usuarios"
branch_labels = None
depends_on = None


def audit_columns():
    return [
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade():
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("account_type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("bank_name", sa.String(120)),
        sa.Column("account_number", sa.String(50)),
        sa.Column("clabe", sa.String(18)),
        sa.Column("card_last_digits", sa.String(4)),
        sa.Column("short_description", sa.String(255)),
        sa.Column("long_description", sa.String(1000)),
        *audit_columns(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "name", name="uq_account_company_name"),
    )
    op.create_index("ix_accounts_company_id", "accounts", ["company_id"])
    op.create_table(
        "concepts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("concept_type", sa.String(10), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("short_description", sa.String(255)),
        sa.Column("long_description", sa.String(1000)),
        *audit_columns(),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "concept_type", "name", name="uq_concept_company_type_name"),
    )
    op.create_index("ix_concepts_company_id", "concepts", ["company_id"])
    op.create_table(
        "account_concepts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "concept_id", name="uq_account_concept"),
    )
    op.create_index("ix_account_concepts_account_id", "account_concepts", ["account_id"])
    op.create_index("ix_account_concepts_concept_id", "account_concepts", ["concept_id"])
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("concept_id", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_by", sa.Integer(), nullable=False),
        sa.Column("short_description", sa.String(255)),
        sa.Column("long_description", sa.String(1000)),
        *audit_columns(),
        sa.CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"]),
        sa.ForeignKeyConstraint(["captured_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_concept_id", "transactions", ["concept_id"])
    op.create_index("ix_transactions_captured_by", "transactions", ["captured_by"])


def downgrade():
    op.drop_table("transactions")
    op.drop_table("account_concepts")
    op.drop_table("concepts")
    op.drop_table("accounts")
