"""
데이터베이스 연결 관리자

SQLAlchemy를 사용한 비동기 데이터베이스 연결 관리
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.engine import Engine

class DatabaseManager:
    """데이터베이스 연결 관리자"""
    
    def __init__(self, database_url: str, **engine_kwargs):
        """
        데이터베이스 매니저 초기화
        
        Args:
            database_url: 데이터베이스 연결 URL
            **engine_kwargs: SQLAlchemy 엔진 추가 옵션
        """
        self.database_url = database_url
        self.engine: Optional[Engine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        
        # 기본 엔진 설정
        engine_options = {
            "echo": engine_kwargs.get("echo", False),
        }
        
        # SQLite가 아닌 경우에만 connection pool 설정 추가
        if not database_url.startswith("sqlite"):
            engine_options.update({
                "pool_size": engine_kwargs.get("pool_size", 10),
                "max_overflow": engine_kwargs.get("max_overflow", 20),
                "pool_pre_ping": True,
                "pool_recycle": 3600,
            })
        
        # 추가 엔진 옵션 적용
        engine_options.update(engine_kwargs)
        
        # 엔진 생성
        self.engine = create_async_engine(database_url, **engine_options)
        
        # 세션 팩토리 생성
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        데이터베이스 세션 컨텍스트 매니저
        
        자동으로 커밋/롤백을 처리합니다.
        """
        if not self.session_factory:
            raise RuntimeError("Database manager not initialized")
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def close(self) -> None:
        """데이터베이스 연결 종료"""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None