import magic

def get_mime_type(file_path: str) -> str:
    return magic.from_file(file_path, mime=True)

def is_allowed_file_type(file_path: str, allowed_types: list[str]) -> bool:
    mime_type = get_mime_type(file_path)
    return mime_type in allowed_types
