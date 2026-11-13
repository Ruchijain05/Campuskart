from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.app_database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.app_database_url,
    connect_args=connect_args,
    pool_pre_ping=not settings.app_database_url.startswith("sqlite"),
)

if engine.dialect.name == "postgresql":
    @event.listens_for(engine, "connect")
    def verify_runtime_database_role(dbapi_connection, _connection_record) -> None:
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SELECT current_user")
            connected_role = cursor.fetchone()[0]
        if connected_role != settings.app_database_role:
            raise RuntimeError(
                "APP_DATABASE_URL connected as PostgreSQL role "
                f"{connected_role!r}, expected APP_DATABASE_ROLE "
                f"{settings.app_database_role!r}."
            )

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
