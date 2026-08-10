from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")

_CATEGORY_NAME_MAX = 40
_TAG_NAME_MAX = 30


def _normalize(name: str, max_len: int) -> str:
    normalized = unicodedata.normalize("NFKC", name)
    normalized = _WHITESPACE.sub(" ", normalized.strip())
    if not normalized:
        raise ValueError("名称不能为空")
    if len(normalized) > max_len:
        raise ValueError("名称过长")
    return normalized


def normalize_category_name(name: str) -> str:
    return _normalize(name, _CATEGORY_NAME_MAX)


def normalize_tag_name(name: str) -> str:
    return _normalize(name, _TAG_NAME_MAX)
