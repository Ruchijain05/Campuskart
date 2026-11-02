"""Add a product image gallery and preserve existing primary image URLs."""

from alembic import op
import sqlalchemy as sa


revision = "0013_product_images"
down_revision = "0012_returns_refunds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name="fk_product_images_product_id_products", ondelete="CASCADE"),
        sa.UniqueConstraint("storage_key", name="uq_product_images_storage_key"),
    )
    op.create_index("ix_product_images_id", "product_images", ["id"])
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])

    connection = op.get_bind()
    products = sa.table("products", sa.column("id", sa.Integer()), sa.column("image_url", sa.String(length=2048)))
    product_images = sa.table(
        "product_images",
        sa.column("product_id", sa.Integer()),
        sa.column("image_url", sa.String(length=2048)),
        sa.column("storage_key", sa.String(length=255)),
        sa.column("is_primary", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    existing_images = connection.execute(
        sa.select(products.c.id, products.c.image_url).where(
            products.c.image_url.is_not(None), products.c.image_url != ""
        )
    ).all()
    for product_id, image_url in existing_images:
        connection.execute(product_images.insert().values(
            product_id=product_id,
            image_url=image_url,
            storage_key=None,
            is_primary=True,
            created_at=sa.func.now(),
        ))


def downgrade() -> None:
    op.drop_index("ix_product_images_product_id", table_name="product_images")
    op.drop_index("ix_product_images_id", table_name="product_images")
    op.drop_table("product_images")
