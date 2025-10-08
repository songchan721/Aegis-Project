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
        self.checks: Dict[str, Callable[[], Awaitable[bool]]] = {}
    
    def add_check(self, name: str, check: Callable[[], Awaitable[bool]]):
        """헬스 체크 추가"""
        self.checks[name] = check
    
    def remove_check(self, name: str):
        """헬스 체크 제거"""
        if name in self.checks:
            del self.checks[name]
    
    async def run_check(self, name: str, check: Callable[[], Awaitable[bool]]) -> HealthCheckResult:
        """개별 헬스 체크 실행"""
        start_time = time.time()
        try:
            result = await check()
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
