from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from decouple import config
DATABASE_URL = config(
    "DATABASE_URL",
    default="postgresql+asyncpg://postgres:postgres@localhost:5432/code_review_bot"
)


engine = create_async_engine(
    DATABASE_URL,
    echo=False, # echo=True — выводит SQL-запросы в лог (удобно для отладки, в проде ставим False)
    pool_size=20,  # размер пула соединений
    max_overflow=10,  # максимум дополнительных соединений
    pool_pre_ping=True,  # проверка соединения перед использованием
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # не очищать объекты после коммита
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()