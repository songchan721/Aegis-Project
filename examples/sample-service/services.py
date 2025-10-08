"""
샘플 서비스 비즈니스 로직
"""

import uuid
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from aegis_shared.database import DatabaseManager
from aegis_shared.cache import CacheClient
from aegis_shared.messaging import EventPublisher
from aegis_shared.monitoring import MetricsCollector
from aegis_shared.logging import get_logger
from aegis_shared.errors.exceptions import EntityNotFoundError, DuplicateEntityError

from models import User, UserRepository

logger = get_logger(__name__)


class UserService:
    """사용자 서비스"""
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_client: CacheClient,
        event_publisher: EventPublisher,
        metrics_collector: MetricsCollector
    ):
        self.db_manager = db_manager
        self.cache = cache_client
        self.event_publisher = event_publisher
        self.metrics = metrics_collector
    
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """사용자 생성"""
        logger.info("Creating user", email=user_data.get("email"))
        
        async with self.db_manager.session() as session:
            user_repo = UserRepository(session, User)
            
            # 중복 이메일 확인
            existing_user = await user_repo.get_by_email(user_data["email"])
            if existing_user:
                raise DuplicateEntityError("User with this email already exists")
            
            # 사용자 생성
            user = User(
                id=str(uuid.uuid4()),
                email=user_data["email"],
                name=user_data["name"],
                phone=user_data.get("phone"),
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            created_user = await user_repo.create(user)
            
            # 캐시에 저장
            await self._cache_user(created_user)
            
            # 이벤트 발행
            await self.event_publisher.publish(
                topic="user-events",
                event_type="user.created",
                data={
                    "user_id": created_user.id,
                    "email": created_user.email,
                    "name": created_user.name,
                    "created_at": created_user.created_at.isoformat()
                },
                key=created_user.id
            )
            
            # 메트릭 기록
            self.metrics.increment_counter(
                "users_created_total",
                labels={"service": "sample-service"}
            )
            
            logger.info("User created successfully", user_id=created_user.id)
            return created_user
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """사용자 조회"""
        logger.debug("Getting user", user_id=user_id)
        
        async with self.db_manager.session() as session:
            user_repo = UserRepository(session, User)
            user = await user_repo.get_by_id(user_id)
            
            if user:
                # 캐시에 저장
                await self._cache_user(user)
            
            return user
    
    @CacheClient.cached(ttl=300)  # 5분 캐시
    async def get_user_cached(self, user_id: str) -> Optional[User]:
        """캐시된 사용자 조회"""
        logger.debug("Getting cached user", user_id=user_id)
        
        # 캐시에서 먼저 조회
        cached_user = await self.cache.get(f"user:{user_id}")
        if cached_user:
            logger.debug("User found in cache", user_id=user_id)
            return User(**cached_user)
        
        # 데이터베이스에서 조회
        user = await self.get_user(user_id)
        if user:
            await self._cache_user(user)
        
        return user
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> Tuple[List[User], int]:
        """사용자 목록 조회"""
        logger.debug("Listing users", skip=skip, limit=limit)
        
        async with self.db_manager.session() as session:
            user_repo = UserRepository(session, User)
            
            users = await user_repo.get_active_users(skip=skip, limit=limit)
            total = await user_repo.count(filters={"is_active": True, "deleted_at": None})
            
            return users, total
    
    async def update_user(self, user_id: str, user_data: Dict[str, Any]) -> Optional[User]:
        """사용자 업데이트"""
        logger.info("Updating user", user_id=user_id)
        
        async with self.db_manager.session() as session:
            user_repo = UserRepository(session, User)
            
            # 기존 사용자 확인
            existing_user = await user_repo.get_by_id(user_id)
            if not existing_user:
                return None
            
            # 업데이트 데이터 준비
            update_data = {k: v for k, v in user_data.items() if v is not None}
            update_data["updated_at"] = datetime.utcnow()
            
            # 사용자 업데이트
            updated_user = await user_repo.update(user_id, **update_data)
            
            if updated_user:
                # 캐시 무효화
                await self.cache.delete(f"user:{user_id}")
                
                # 이벤트 발행
                await self.event_publisher.publish(
                    topic="user-events",
                    event_type="user.updated",
                    data={
                        "user_id": updated_user.id,
                        "changes": update_data,
                        "updated_at": updated_user.updated_at.isoformat()
                    },
                    key=updated_user.id
                )
                
                # 메트릭 기록
                self.metrics.increment_counter(
                    "users_updated_total",
                    labels={"service": "sample-service"}
                )
                
                logger.info("User updated successfully", user_id=user_id)
            
            return updated_user
    
    async def delete_user(self, user_id: str) -> bool:
        """사용자 삭제 (소프트 삭제)"""
        logger.info("Deleting user", user_id=user_id)
        
        async with self.db_manager.session() as session:
            user_repo = UserRepository(session, User)
            
            # 기존 사용자 확인
            existing_user = await user_repo.get_by_id(user_id)
            if not existing_user:
                return False
            
            # 소프트 삭제
            deleted_user = await user_repo.soft_delete(user_id)
            
            if deleted_user:
                # 캐시에서 제거
                await self.cache.delete(f"user:{user_id}")
                
                # 이벤트 발행
                await self.event_publisher.publish(
                    topic="user-events",
                    event_type="user.deleted",
                    data={
                        "user_id": user_id,
                        "deleted_at": deleted_user.deleted_at.isoformat()
                    },
                    key=user_id
                )
                
                # 메트릭 기록
                self.metrics.increment_counter(
                    "users_deleted_total",
                    labels={"service": "sample-service"}
                )
                
                logger.info("User deleted successfully", user_id=user_id)
                return True
            
            return False
    
    async def search_users(self, search_term: str, skip: int = 0, limit: int = 100) -> Tuple[List[User], int]:
        """사용자 검색"""
        logger.debug("Searching users", search_term=search_term, skip=skip, limit=limit)
        
        async with self.db_manager.session() as session:
            user_repo = UserRepository(session, User)
            
            users = await user_repo.search_users(search_term, skip=skip, limit=limit)
            
            # 검색 결과 개수는 별도 쿼리로 조회 (실제 구현에서는 최적화 필요)
            total = len(users)  # 간단한 구현
            
            # 메트릭 기록
            self.metrics.increment_counter(
                "user_searches_total",
                labels={"service": "sample-service"}
            )
            
            return users, total
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """사용자 통계 조회"""
        logger.debug("Getting user statistics")
        
        async with self.db_manager.session() as session:
            user_repo = UserRepository(session, User)
            
            total_users = await user_repo.count()
            active_users = await user_repo.count(filters={"is_active": True, "deleted_at": None})
            inactive_users = total_users - active_users
            
            stats = {
                "total_users": total_users,
                "active_users": active_users,
                "inactive_users": inactive_users,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # 통계를 캐시에 저장 (1시간)
            await self.cache.set("user_statistics", stats, ttl=3600)
            
            return stats
    
    async def _cache_user(self, user: User) -> None:
        """사용자를 캐시에 저장"""
        user_data = {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "phone": user.phone,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
            "deleted_at": user.deleted_at.isoformat() if user.deleted_at else None
        }
        
        await self.cache.set(f"user:{user.id}", user_data, ttl=1800)  # 30분 캐시