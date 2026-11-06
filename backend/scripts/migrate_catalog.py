from sqlalchemy import MetaData, Table, create_engine, func, insert, select, text
from sqlalchemy.engine import Connection, Engine

from app import models
from app.core.config import settings
from app.core.database import engine as target_engine

target_metadata = models.User.metadata


def _copy_table(
    source_engine: Engine,
    target_connection: Connection,
    table_name: str,
) -> int:
    source_metadata = MetaData()
    with source_engine.connect() as source_connection:
        source_table = Table(
            table_name,
            source_metadata,
            autoload_with=source_connection,
        )
        source_rows = source_connection.execute(select(source_table)).mappings().all()

    target_table = target_metadata.tables[table_name]
    copy_columns = [
        column.name
        for column in target_table.columns
        if column.name in source_table.c and column.name != "seller_id"
    ]
    rows = [
        {column: row[column] for column in copy_columns}
        for row in source_rows
    ]
    parent_links = []
    if table_name == "categories" and "parent_id" in copy_columns:
        parent_links = [(row["id"], row["parent_id"]) for row in rows]
        for row in rows:
            row["parent_id"] = None
    if table_name == "products":
        for row in rows:
            row["seller_id"] = None

    if rows:
        target_connection.execute(insert(target_table), rows)
    if parent_links:
        for category_id, parent_id in parent_links:
            target_connection.execute(
                target_table.update()
                .where(target_table.c.id == category_id)
                .values(parent_id=parent_id)
            )
    return len(rows)


def main() -> None:
    if settings.mysql_source_url is None:
        raise SystemExit("Set MYSQL_SOURCE_URL to the current MySQL database before running this script.")
    if target_engine.dialect.name != "postgresql":
        raise SystemExit("DATABASE_URL must point to the Supabase PostgreSQL database.")

    source_engine = create_engine(
        settings.mysql_source_url.get_secret_value(),
        pool_pre_ping=True,
    )
    if source_engine.dialect.name != "mysql":
        raise SystemExit("MYSQL_SOURCE_URL must use a MySQL-compatible SQLAlchemy URL.")

    try:
        with target_engine.begin() as target_connection:
            for table_name in ("categories", "products"):
                target_table = target_metadata.tables[table_name]
                count = target_connection.scalar(
                    select(func.count()).select_from(target_table)
                )
                if count:
                    raise SystemExit(
                        f"Supabase table {table_name!r} is not empty; "
                        "catalog migration only runs against empty catalog tables."
                    )

            category_count = _copy_table(source_engine, target_connection, "categories")
            product_count = _copy_table(source_engine, target_connection, "products")
            for table_name in ("categories", "products"):
                target_connection.execute(
                    text(
                        "SELECT setval("
                        f"pg_get_serial_sequence('public.{table_name}', 'id'), "
                        f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL"
                        f") FROM public.{table_name}"
                    )
                )
    finally:
        source_engine.dispose()

    print(f"Catalog migration complete: {category_count} categories, {product_count} products.")
    print("Existing seller ownership was cleared; image_url values were preserved.")


if __name__ == "__main__":
    main()
