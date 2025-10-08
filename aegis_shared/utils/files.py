"""
파일 유틸리티 모듈

Note: 이 모듈은 python-magic 라이브러리를 사용합니다.
Windows에서는 python-magic-bin 패키지를 설치하거나,
libmagic 바이너리를 수동으로 설치해야 합니다.
"""

try:
    import magic
    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    # Windows에서 libmagic이 없는 경우
    MAGIC_AVAILABLE = False
    magic = None


def get_mime_type(file_path: str) -> str:
    """
    파일의 MIME 타입을 반환합니다.
    
    Args:
        file_path: 파일 경로
        
    Returns:
        MIME 타입 문자열
        
    Raises:
        ImportError: python-magic 라이브러리를 사용할 수 없는 경우
    """
    if not MAGIC_AVAILABLE:
        raise ImportError(
            "python-magic library is not available. "
            "On Windows, install python-magic-bin: pip install python-magic-bin"
        )
    return magic.from_file(file_path, mime=True)


def is_allowed_file_type(file_path: str, allowed_types: list[str]) -> bool:
    """
    파일 타입이 허용된 타입인지 확인합니다.
    
    Args:
        file_path: 파일 경로
        allowed_types: 허용된 MIME 타입 리스트
        
    Returns:
        허용된 타입이면 True, 아니면 False
        
    Raises:
        ImportError: python-magic 라이브러리를 사용할 수 없는 경우
    """
    mime_type = get_mime_type(file_path)
    return mime_type in allowed_types
