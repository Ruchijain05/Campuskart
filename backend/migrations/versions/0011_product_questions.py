"""Add buyer product questions and seller answers."""

from alembic import op
import sqlalchemy as sa


revision = "0011_product_questions"
down_revision = "0010_seller_fulfillment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_product_questions_product_id_products", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], name="fk_product_questions_buyer_id_users", ondelete="CASCADE"),
    )
    op.create_index("ix_product_questions_id", "product_questions", ["id"])
    op.create_index("ix_product_questions_product_id", "product_questions", ["product_id"])
    op.create_index("ix_product_questions_buyer_id", "product_questions", ["buyer_id"])


def downgrade() -> None:
    op.drop_index("ix_product_questions_buyer_id", table_name="product_questions")
    op.drop_index("ix_product_questions_product_id", table_name="product_questions")
    op.drop_index("ix_product_questions_id", table_name="product_questions")
    op.drop_table("product_questions")
