"""Add category hierarchy and seed example student categories.

Revision ID: 0003_category_hierarchy
Revises: 0002_auth
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_category_hierarchy"
down_revision = "0002_auth"
branch_labels = None
depends_on = None


def _get_or_create_category(
    connection: sa.Connection,
    categories: sa.Table,
    *,
    name: str,
    parent_id: int | None,
) -> int:
    row = connection.execute(
        sa.select(categories.c.id, categories.c.parent_id).where(
            sa.func.lower(categories.c.name) == name.casefold()
        )
    ).first()
    if row is not None:
        category_id, existing_parent_id = row
        if parent_id is not None and existing_parent_id is None:
            connection.execute(
                categories.update()
                .where(categories.c.id == category_id)
                .values(parent_id=parent_id)
            )
        return category_id

    connection.execute(
        categories.insert().values(name=name, description=None, parent_id=parent_id)
    )
    return connection.execute(
        sa.select(categories.c.id).where(
            sa.func.lower(categories.c.name) == name.casefold()
        )
    ).scalar_one()


def upgrade() -> None:
    with op.batch_alter_table("categories") as batch_op:
        batch_op.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_categories_parent_id_categories",
            "categories",
            ["parent_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_categories_parent_id", ["parent_id"])

    connection = op.get_bind()
    categories = sa.table(
        "categories",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String(length=100)),
        sa.column("description", sa.String(length=500)),
        sa.column("parent_id", sa.Integer()),
    )
    for root_name, branch_name, leaf_name in (
        ("Electronics", "Mobiles", "Chargers"),
        ("Grocery", "Snacks", "Biscuits"),
        ("Stationery", "Pens", "Notebooks"),
    ):
        root_id = _get_or_create_category(
            connection,
            categories,
            name=root_name,
            parent_id=None,
        )
        branch_id = _get_or_create_category(
            connection,
            categories,
            name=branch_name,
            parent_id=root_id,
        )
        _get_or_create_category(
            connection,
            categories,
            name=leaf_name,
            parent_id=branch_id,
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE categories SET parent_id = NULL WHERE parent_id IS NOT NULL")
    )
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_index("ix_categories_parent_id")
        batch_op.drop_constraint("fk_categories_parent_id_categories", type_="foreignkey")
        batch_op.drop_column("parent_id")
