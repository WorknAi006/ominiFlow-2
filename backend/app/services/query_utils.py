"""Shared query helpers for services."""


def escape_like(value: str) -> str:
    """Escape LIKE wildcards so user input is matched literally (escape="\\")."""
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def like_pattern(value: str) -> str:
    return f"%{escape_like(value)}%"


def page_offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size
