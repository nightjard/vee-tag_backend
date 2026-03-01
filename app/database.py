from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import DBAPIError
from app.config import settings
from app.models import Base
import logging

logger = logging.getLogger(__name__)

# Создаем async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    poolclass=NullPool,
)

# Создаем async session maker
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """Dependency для получения сессии БД"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Инициализация БД - создание таблиц и PostGIS"""
    async with engine.begin() as conn:
        # Создаем расширение PostGIS — используем sqlalchemy.text()
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        except DBAPIError as exc:
            # Если у пользователя нет прав - логируем и продолжаем.
            # В production лучше предварительно создать расширение отдельно.
            logger.warning("Не удалось создать расширение postgis: %s", exc)
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)
