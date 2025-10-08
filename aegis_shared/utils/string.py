import re

def to_slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[\s_-]+", "-", s)
    s = re.sub(r"[^a-z0-9-]", "", s)
    return s
