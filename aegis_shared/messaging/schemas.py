from typing import Dict, Any, Optional
from datetime import datetime, UTC
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from uuid import UUID

# EventSchema는 VersionedEvent의 별칭
EventSchema = None  # 나중에 정의됨

class EventMetadata(BaseModel):
    """이벤트 메타데이터"""

    service_name: Optional[str] = Field(None, description="서비스 이름")
    correlation_id: Optional[str] = Field(None, description="상관관계 ID")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    request_id: Optional[str] = Field(None, description="요청 ID")
    trace_id: Optional[str] = Field(None, description="추적 ID")
    span_id: Optional[str] = Field(None, description="스팬 ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="메타데이터 생성 시간")

    @field_serializer('timestamp')
    def serialize_timestamp(self, v: datetime) -> str:
        return v.isoformat()

class VersionedEvent(BaseModel):
    """버전이 관리되는 이벤트 베이스 클래스"""

    event_type: str = Field(..., description="이벤트 타입")
    version: str = Field(..., description="이벤트 스키마 버전")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC), description="이벤트 발생 시간")
    source: str = Field(..., description="이벤트 발행 서비스")
    data: Dict[str, Any] = Field(..., description="이벤트 데이터")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")

    @field_serializer('timestamp')
    def serialize_timestamp(self, v: datetime) -> str:
        return v.isoformat()

class EventMessage(BaseModel):
    """이벤트 메시지"""

    topic: str = Field(..., description="토픽 이름")
    key: Optional[str] = Field(None, description="메시지 키")
    value: VersionedEvent = Field(..., description="이벤트 데이터")
    headers: Dict[str, str] = Field(default_factory=dict, description="헤더")

class EventSubscription(BaseModel):
    """이벤트 구독 정보"""

    topic: str = Field(..., description="구독할 토픽")
    group_id: str = Field(..., description="컨슈머 그룹 ID")
    handler: str = Field(..., description="핸들러 함수 이름")
    auto_commit: bool = Field(default=True, description="자동 커밋 여부")
    options: Dict[str, Any] = Field(default_factory=dict, description="추가 옵션")

class DeadLetterEvent(BaseModel):
    """Dead Letter 이벤트"""

    original_event: VersionedEvent = Field(..., description="원본 이벤트")
    error_message: str = Field(..., description="에러 메시지")
    error_type: str = Field(..., description="에러 타입")
    retry_count: int = Field(default=0, description="재시도 횟수")
    first_failure: datetime = Field(..., description="최초 실패 시간")
    last_failure: datetime = Field(..., description="최종 실패 시간")

    @field_serializer('first_failure', 'last_failure')
    def serialize_datetime(self, v: datetime) -> str:
        return v.isoformat()

# EventSchema를 VersionedEvent의 별칭으로 설정
EventSchema = VersionedEvent