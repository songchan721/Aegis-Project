"""
직렬화 유틸리티

Pydantic 모델의 JSON/dict/ORM 변환을 위한 헬퍼 함수를 제공합니다.
Pydantic v2 API를 사용합니다.
"""

import json
from datetime import datetime
from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def from_orm(orm_obj: Any, pydantic_model: Type[T]) -> T:
    """
    ORM 객체를 Pydantic 모델로 변환

    Args:
        orm_obj: SQLAlchemy ORM 객체
        pydantic_model: 변환할 Pydantic 모델 클래스

    Returns:
        Pydantic 모델 인스턴스

    Example:
        >>> user_model = from_orm(user_orm, UserProfile)
    """
    return pydantic_model.model_validate(orm_obj)


def to_dict(pydantic_obj: BaseModel, exclude_none: bool = False) -> Dict[str, Any]:
    """
    Pydantic 모델을 dict로 변환

    Args:
        pydantic_obj: Pydantic 모델 인스턴스
        exclude_none: None 값을 제외할지 여부

    Returns:
        dict 형태의 데이터

    Example:
        >>> data = to_dict(user_profile)
    """
    return pydantic_obj.model_dump(exclude_none=exclude_none)


def to_json(pydantic_obj: BaseModel, exclude_none: bool = False) -> str:
    """
    Pydantic 모델을 JSON 문자열로 변환

    Args:
        pydantic_obj: Pydantic 모델 인스턴스
        exclude_none: None 값을 제외할지 여부

    Returns:
        JSON 문자열

    Example:
        >>> json_str = to_json(user_profile)
    """
    return pydantic_obj.model_dump_json(exclude_none=exclude_none)


def json_serial(obj: Any) -> str:
    """
    JSON 직렬화를 위한 기본 핸들러

    Args:
        obj: 직렬화할 객체

    Returns:
        직렬화된 문자열

    Raises:
        TypeError: 지원하지 않는 타입인 경우
    """
    from uuid import UUID

    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def to_json_custom(pydantic_obj: BaseModel) -> str:
    """
    커스텀 JSON 직렬화 (datetime 처리 포함)

    Args:
        pydantic_obj: Pydantic 모델 인스턴스

    Returns:
        JSON 문자열

    Example:
        >>> json_str = to_json_custom(user_profile)
    """
    return json.dumps(pydantic_obj.model_dump(), default=json_serial)
