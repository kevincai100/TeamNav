from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


@dataclass(frozen=True)
class Database:
    engine: AsyncEngine
    sessions: async_sessionmaker[AsyncSession]


def create_database(url: str) -> Database:
    engine = create_async_engine(url, pool_pre_ping=True)
    return Database(engine=engine, sessions=async_sessionmaker(engine, expire_on_commit=False))


async def init_models(engine: AsyncEngine) -> None:
    from app import models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def session_dependency(database: Database) -> AsyncIterator[AsyncSession]:
    async with database.sessions() as session:
        yield session
