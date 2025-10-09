"""
페이지네이션 유틸리티

이 모듈은 페이지네이션 관련 헬퍼 함수를 제공합니다.
"""

from typing import List, TypeVar

from aegis_shared.models.pagination import PaginatedResponse

T = TypeVar("T")


def calculate_offset(page: int, page_size: int) -> int:
    """
    페이지 번호와 페이지 크기로부터 오프셋을 계산합니다.

    Args:
        page: 페이지 번호 (1부터 시작)
        page_size: 페이지당 항목 수

    Returns:
        데이터베이스 쿼리에 사용할 오프셋
    """
    if page < 1:
        page = 1
    return (page - 1) * page_size


def calculate_total_pages(total: int, page_size: int) -> int:
    """
    전체 항목 수와 페이지 크기로부터 전체 페이지 수를 계산합니다.

    Args:
        total: 전체 항목 수
        page_size: 페이지당 항목 수

    Returns:
        전체 페이지 수
    """
    if page_size <= 0:
        return 0
    return (total + page_size - 1) // page_size


def paginate(
    items: List[T], total: int, page: int, page_size: int
) -> PaginatedResponse[T]:
    """
    항목 리스트를 페이지네이션 응답으로 변환합니다.

    Args:
        items: 현재 페이지의 항목 리스트
        total: 전체 항목 수
        page: 현재 페이지 번호 (1부터 시작)
        page_size: 페이지당 항목 수

    Returns:
        페이지네이션 응답 객체
    """
    return PaginatedResponse.create(
        items=items, total=total, page=page, page_size=page_size
    )


def validate_pagination_params(
    page: int, page_size: int, max_page_size: int = 100
) -> tuple[int, int]:
    """
    페이지네이션 파라미터를 검증하고 정규화합니다.

    Args:
        page: 페이지 번호
        page_size: 페이지당 항목 수
        max_page_size: 최대 페이지 크기 (기본값: 100)

    Returns:
        검증된 (page, page_size) 튜플
    """
    # 페이지 번호는 최소 1
    validated_page = max(1, page)

    # 페이지 크기는 1에서 max_page_size 사이
    validated_page_size = max(1, min(page_size, max_page_size))

    return validated_page, validated_page_size
