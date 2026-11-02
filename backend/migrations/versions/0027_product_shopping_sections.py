"""Add independent shopping sections and product assignments."""

from alembic import op
import sqlalchemy as sa


revision = "0027_product_sections"
down_revision = "0026_remove_used_market"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopping_sections",
        sa.Column("slug", sa.String(length=32), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
    )
    op.create_table(
        "product_section_assignments",
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("section_slug", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_slug"], ["shopping_sections.slug"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id", "section_slug"),
    )
    op.create_index(
        "ix_product_section_assignments_section_slug",
        "product_section_assignments",
        ["section_slug"],
    )

    sections = sa.table(
        "shopping_sections",
        sa.column("slug", sa.String(length=32)),
        sa.column("name", sa.String(length=100)),
    )
    op.bulk_insert(sections, [
        {"slug": "male", "name": "Male"},
        {"slug": "female", "name": "Female"},
        {"slug": "special_gifts", "name": "Special Gifts"},
    ])


def downgrade() -> None:
    op.drop_index(
        "ix_product_section_assignments_section_slug",
        table_name="product_section_assignments",
    )
    op.drop_table("product_section_assignments")
    op.drop_table("shopping_sections")
