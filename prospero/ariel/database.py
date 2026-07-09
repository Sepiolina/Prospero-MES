from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

SQLALCHEMY_DATABASE_URL = "sqlite:///static/ariel.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=NullPool,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.close()


SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass
