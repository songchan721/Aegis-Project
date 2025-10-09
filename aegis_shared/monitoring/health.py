from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Callable, Awaitable, Optional, List
from enum import Enum
from pydantic import BaseModel
import asyncio
import time

router = APIRouter()

health_checks: Dict[str, Callable[[], Awaitable[bool]]] = {}

class HealthStatus(Enum):
    """헬스 체크 상태"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"

class HealthCheckResult(BaseModel):
    """헬스 체크 결과"""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    duration_ms: Optional[float] = None

class HealthChecker:
    """헬스 체크 관리자"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}

    def register_check(self, name: str, check: Callable):
        """헬스 체크 등록

        Args:
            name: 체크 이름
            check: (HealthStatus, message) 튜플을 반환하는 함수
        """
        self.checks[name] = check

    def add_check(self, name: str, check: Callable[[], Awaitable[bool]]):
        """헬스 체크 추가 (레거시 API)"""
        self.checks[name] = check
    
    def remove_check(self, name: str):
        """헬스 체크 제거"""
        if name in self.checks:
            del self.checks[name]
    
    async def run_check(self, name: str, check: Callable) -> HealthCheckResult:
        """개별 헬스 체크 실행"""
        start_time = time.time()
        try:
            # 체크 함수가 (status, message) 튜플을 반환하는 경우
            result = check()
            if isinstance(result, tuple) and len(result) == 2:
                status, message = result
                duration = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    name=name,
                    status=status,
                    message=message,
                    duration_ms=duration
                )
            # 체크 함수가 bool을 반환하는 경우 (레거시)
            elif isinstance(result, bool):
                duration = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    duration_ms=duration
                )
            # async 함수인 경우
            else:
                result = await result
                duration = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    duration_ms=duration
                )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                duration_ms=duration
            )

    async def check_health(self):
        """모든 헬스 체크 실행하고 결과 반환

        Returns:
            (overall_status, details): 전체 상태와 각 체크별 상세 정보
        """
        if not self.checks:
            return HealthStatus.HEALTHY, {}

        results = {}
        statuses = []

        for name, check in self.checks.items():
            result = await self.run_check(name, check)
            results[name] = {
                "status": result.status,
                "message": result.message
            }
            statuses.append(result.status)

        # 전체 상태 결정
        if all(s == HealthStatus.HEALTHY for s in statuses):
            overall_status = HealthStatus.HEALTHY
        elif any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        else:
            overall_status = HealthStatus.DEGRADED

        return overall_status, results

    async def check_all(self) -> List[HealthCheckResult]:
        """모든 헬스 체크 실행"""
        if not self.checks:
            return []
        
        tasks = [
            self.run_check(name, check) 
            for name, check in self.checks.items()
        ]
        
        return await asyncio.gather(*tasks)
    
    async def get_overall_status(self) -> HealthStatus:
        """전체 헬스 상태 조회"""
        results = await self.check_all()
        
        if not results:
            return HealthStatus.HEALTHY
        
        unhealthy_count = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)
        
        if unhealthy_count == 0:
            return HealthStatus.HEALTHY
        elif unhealthy_count < len(results):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

def add_health_check(name: str, check: Callable[[], Awaitable[bool]]):
    health_checks[name] = check

@router.get("/health")
async def health_check():
    results = {}
    status_code = 200
    for name, check in health_checks.items():
        try:
            results[name] = "ok" if await check() else "error"
            if results[name] == "error":
                status_code = 503
        except Exception:
            results[name] = "error"
            status_code = 503
    return results, status_code