from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import SQLAlchemyError
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from asr_trading.core.security import SecretsManager
from asr_trading.core.logger import logger

class Base(DeclarativeBase):
    pass

class HotStore:
    """
    Manages the 'Hot' database (Postgres) for live state (Positions, Orders).
    """
    def __init__(self):
        self.engine = None
        self.session_factory = None

    def initialize(self):
        db_url = SecretsManager.get_secret("DATABASE_URL", default="postgresql+asyncpg://user:password@localhost:5432/asr_db")
        try:
            self.engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
            self.session_factory = async_sessionmaker(bind=self.engine, expire_on_commit=False)
            logger.info("HotStore: Connected to Postgres.")
        except Exception as e:
            logger.critical(f"HotStore Connection Failed: {e}")
            raise e

    async def create_tables(self):
        """Creates all tables defined in Base metadata."""
        if not self.engine:
            self.initialize()
            
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("HotStore: Schema created/verified.")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self.session_factory:
            self.initialize()
            
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f"Database Session Error: {e}")
                raise e
            finally:
                await session.close()
    
    async def close(self):
        if self.engine:
            await self.engine.dispose()

db = HotStore()
