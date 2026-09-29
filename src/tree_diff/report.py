from collections.abc import Iterable
from json import dump
from typing import Any


def _strip_diff_values(obj: Any, keep: Iterable[str] | None = None) -> Any:
    keep_set = set(keep or [])

    if isinstance(obj, list):
        return [_strip_diff_values(item, keep_set) for item in obj]
    if isinstance(obj, dict):
        return {
            key: value for key, value in obj.items() if not keep_set or key in keep_set
        }
    return obj


def save_to_file(obj: Any, filename: str, keep: Iterable[str] | None = None) -> None:
    cleaned = _strip_diff_values(obj, keep)
    with open(filename, "w", encoding="utf-8") as fp:
        dump(obj=cleaned, fp=fp, indent=3, sort_keys=True)
