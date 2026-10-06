"""
Sanitize decoded JSON before storing it in PostgreSQL.

PostgreSQL text and JSONB cannot store U+0000 (NUL). A JSON body may
legally contain the escape "\\u0000", which json.loads turns into a real
NUL character; storing it fails the whole insert. strip_nul() removes NUL
from every string value and object key and changes nothing else (newlines,
tabs, emoji and all other Unicode are preserved).

Iterative rather than recursive, so deeply nested input cannot raise
RecursionError here.
"""
from typing import Any

NUL = "\x00"


def strip_nul(value: Any) -> tuple[Any, int]:
    """
    Return (sanitized copy, number of NUL characters removed).

    - Strings: NUL removed.
    - Dict keys: NUL removed. A key that needed cleaning never overrides an
      originally clean key with the same name (nor an earlier cleaned one).
    - Lists and dicts are rebuilt; other JSON scalars are returned as-is.
    """

    removed = 0
    # (source container, new container) pairs still to fill.
    stack: list[tuple[Any, Any]] = []

    def convert(item: Any) -> Any:
        nonlocal removed
        if isinstance(item, str):
            count = item.count(NUL)
            if count:
                removed += count
                return item.replace(NUL, "")
            return item
        if isinstance(item, dict):
            child: dict | list = {}
        elif isinstance(item, list):
            child = []
        else:
            return item
        stack.append((item, child))
        return child

    root = convert(value)

    while stack:
        source, target = stack.pop()

        if isinstance(source, dict):
            for key, item in source.items():
                clean_key = key
                if isinstance(key, str) and NUL in key:
                    removed += key.count(NUL)
                    clean_key = key.replace(NUL, "")
                    if clean_key in source or clean_key in target:
                        continue
                target[clean_key] = convert(item)
        else:
            for item in source:
                target.append(convert(item))

    return root, removed
