"""
민감 데이터 마스킹 유틸리티

개인정보 및 민감 데이터의 안전한 직렬화를 지원합니다.
"""

import re
from typing import Annotated, Any, Optional

from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema


def mask_email(email: str) -> str:
    """
    이메일 주소를 마스킹합니다.

    Args:
        email: 마스킹할 이메일 주소

    Returns:
        마스킹된 이메일 (예: "te**@example.com")

    Example:
        >>> mask_email("test@example.com")
        'te**@example.com'
    """
    if not email or "@" not in email:
        return "***"

    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "**"
    else:
        masked_local = local[:2] + "**"

    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    """
    전화번호를 마스킹합니다.

    Args:
        phone: 마스킹할 전화번호

    Returns:
        마스킹된 전화번호 (예: "010-****-5678")

    Example:
        >>> mask_phone("010-1234-5678")
        '010-****-5678'
    """
    if not phone:
        return "***"

    # 숫자만 추출
    digits = re.sub(r"\D", "", phone)

    if len(digits) < 8:
        return "***-****-****"

    # 마지막 4자리만 표시
    if len(digits) == 11:  # 010-1234-5678
        return f"{digits[:3]}-****-{digits[-4:]}"
    elif len(digits) == 10:  # 02-1234-5678
        return f"{digits[:2]}-****-{digits[-4:]}"
    else:
        return f"***-****-{digits[-4:]}"


def mask_password(password: str) -> str:
    """
    비밀번호를 완전히 마스킹합니다.

    Args:
        password: 마스킹할 비밀번호

    Returns:
        마스킹된 비밀번호 (항상 "********")

    Example:
        >>> mask_password("mySecurePassword123")
        '********'
    """
    return "********"


def mask_credit_card(card_number: str) -> str:
    """
    신용카드 번호를 마스킹합니다.

    Args:
        card_number: 마스킹할 신용카드 번호

    Returns:
        마스킹된 신용카드 번호 (마지막 4자리만 표시)

    Example:
        >>> mask_credit_card("1234-5678-9012-3456")
        '****-****-****-3456'
    """
    if not card_number:
        return "****-****-****-****"

    # 숫자만 추출
    digits = re.sub(r"\D", "", card_number)

    if len(digits) < 4:
        return "****-****-****-****"

    # 마지막 4자리만 표시
    return f"****-****-****-{digits[-4:]}"


def mask_ssn(ssn: str) -> str:
    """
    주민등록번호를 마스킹합니다.

    Args:
        ssn: 마스킹할 주민등록번호

    Returns:
        마스킹된 주민등록번호 (앞 6자리만 표시)

    Example:
        >>> mask_ssn("123456-1234567")
        '123456-*******'
    """
    if not ssn:
        return "******-*******"

    if "-" in ssn:
        parts = ssn.split("-", 1)
        return f"{parts[0]}-*******"
    elif len(ssn) >= 6:
        return f"{ssn[:6]}-*******"
    else:
        return "******-*******"


def mask_field(value: Any, field_type: str) -> str:
    """
    필드 타입에 따라 자동으로 마스킹합니다.

    Args:
        value: 마스킹할 값
        field_type: 필드 타입 (email, phone, password, credit_card, ssn)

    Returns:
        마스킹된 문자열

    Example:
        >>> mask_field("test@example.com", "email")
        'te**@example.com'
    """
    if value is None:
        return "***"

    value_str = str(value)

    masking_functions = {
        "email": mask_email,
        "phone": mask_phone,
        "password": mask_password,
        "credit_card": mask_credit_card,
        "ssn": mask_ssn,
    }

    mask_func = masking_functions.get(field_type)
    if mask_func:
        return mask_func(value_str)

    # 기본 마스킹: 앞 2자리만 표시
    if len(value_str) <= 2:
        return "***"
    return f"{value_str[:2]}{'*' * (len(value_str) - 2)}"


# Pydantic Annotated 타입 정의
def _mask_serializer(value: str) -> str:
    """민감 데이터 직렬화 시 마스킹"""
    return "********"


MaskedEmail = Annotated[
    str,
    PlainSerializer(lambda x: mask_email(x), return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "format": "email", "example": "us**@example.com"}),
]

MaskedPhone = Annotated[
    str,
    PlainSerializer(lambda x: mask_phone(x), return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "example": "010-****-5678"}),
]

MaskedPassword = Annotated[
    str,
    PlainSerializer(lambda x: mask_password(x), return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "format": "password", "example": "********"}),
]

MaskedCreditCard = Annotated[
    str,
    PlainSerializer(lambda x: mask_credit_card(x), return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "example": "****-****-****-1234"}),
]

MaskedSSN = Annotated[
    str,
    PlainSerializer(lambda x: mask_ssn(x), return_type=str, when_used="json"),
    WithJsonSchema({"type": "string", "example": "123456-*******"}),
]
