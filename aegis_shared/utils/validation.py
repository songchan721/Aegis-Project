import re


def is_email(s: str) -> bool:
    return re.match(r"[^@]+@[^@]+\.[^@]+", s) is not None


def is_phone_number(s: str) -> bool:
    # This is a simple example, a more robust regex might be needed
    return re.match(r"^\+?[0-9]{10,15}$", s) is not None


def is_strong_password(s: str) -> bool:
    # Example: at least 8 characters, one uppercase, one lowercase, one digit
    return (
        len(s) >= 8
        and re.search(r"[a-z]", s) is not None
        and re.search(r"[A-Z]", s) is not None
        and re.search(r"[0-9]", s) is not None
    )
