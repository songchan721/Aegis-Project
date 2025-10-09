"""
이지스(Aegis) 공유 라이브러리 - 유틸리티 모듈

이 모듈은 자주 사용하는 유틸리티 함수들을 제공합니다:
- 시간 유틸리티: UTC 처리, 파싱, 포맷팅
- 문자열 유틸리티: 슬러그 생성, 정규화
- 암호화 유틸리티: 비밀번호 해싱, 암호화/복호화
- 파일 유틸리티: MIME 타입 감지, 파일 검증
- 검증 유틸리티: 이메일, 전화번호, 비밀번호 강도
- 페이지네이션 유틸리티: 오프셋 계산, 페이지네이션 응답 생성
"""

from .time import (
    utcnow,
    to_utc,
    format_datetime,
    parse_datetime
)
from .string import to_slug
from .crypto import (
    hash_password,
    check_password,
    generate_key,
    encrypt,
    decrypt
)
from .files import (
    get_mime_type,
    is_allowed_file_type
)
from .validation import (
    is_email,
    is_phone_number,
    is_strong_password
)
from .pagination import (
    calculate_offset,
    calculate_total_pages,
    paginate,
    validate_pagination_params
)

__all__ = [
    # 암호화 유틸리티
    'hash_password',
    'check_password',
    'generate_key',
    'encrypt',
    'decrypt',
    # 시간 유틸리티
    'utcnow',
    'to_utc',
    'format_datetime',
    'parse_datetime',
    # 문자열 유틸리티
    'to_slug',
    # 파일 유틸리티
    'get_mime_type',
    'is_allowed_file_type',
    # 검증 유틸리티
    'is_email',
    'is_phone_number',
    'is_strong_password',
    # 페이지네이션 유틸리티
    'calculate_offset',
    'calculate_total_pages',
    'paginate',
    'validate_pagination_params',
]