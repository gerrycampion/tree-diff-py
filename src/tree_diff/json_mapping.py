from json import JSONDecodeError, JSONDecoder
from json import load as load_json
from pathlib import Path
from typing import Any

from tree_diff.tree import SourceRange, TreeMapping, TreeNode


def _skip_whitespace(source: str, index: int) -> int:
    while index < len(source) and source[index].isspace():
        index += 1
    return index


def _json_tree(
    source: str, index: int
) -> tuple[SourceRange, dict[str, object] | list[object] | None]:
    start = _skip_whitespace(source, index)
    character = source[start]
    if character == "{":
        children: dict[str, object] = {}
        cursor = _skip_whitespace(source, start + 1)
        while cursor < len(source) and source[cursor] != "}":
            key, key_end = JSONDecoder().raw_decode(source, cursor)
            cursor = _skip_whitespace(source, key_end)
            cursor = _skip_whitespace(source, cursor + 1)
            child_range, child = _json_tree(source, cursor)
            children[key] = (child_range, child)
            cursor = _skip_whitespace(source, child_range[1])
            if source[cursor] == ",":
                cursor = _skip_whitespace(source, cursor + 1)
        return (start, cursor + 1), children
    if character == "[":
        children = []
        cursor = _skip_whitespace(source, start + 1)
        while cursor < len(source) and source[cursor] != "]":
            child_range, child = _json_tree(source, cursor)
            children.append((child_range, child))
            cursor = _skip_whitespace(source, child_range[1])
            if source[cursor] == ",":
                cursor = _skip_whitespace(source, cursor + 1)
        return (start, cursor + 1), children
    _, end = JSONDecoder().raw_decode(source, start)
    return (start, end), None


def _escape_pointer_segment(segment: str) -> str:
    return segment.replace("~", "~0").replace("/", "~1")


class JSONMapping(TreeMapping):
    FILE_EXTENSION = ".json"

    @classmethod
    def load_from_file(cls, filename: str | Path) -> Any:
        with open(filename, encoding="utf-8") as source:
            return load_json(source)

    def to_tree(self, value: Any) -> TreeNode:
        if isinstance(value, dict):
            return TreeNode(
                "object",
                children={
                    str(key): self.to_tree(child) for key, child in value.items()
                },
            )
        if isinstance(value, (list, tuple)):
            return TreeNode("array", children=[self.to_tree(child) for child in value])
        return TreeNode("scalar", value=value)

    def child_path(self, path: str, parent: TreeNode, key: str) -> str:
        return f"{path}/{_escape_pointer_segment(key)}"

    def _path_to_range(self, source: str, path: str) -> SourceRange | None:
        try:
            root_range, children = _json_tree(source, 0)
            tokens = [
                token.replace("~1", "/").replace("~0", "~")
                for token in path.split("/")
                if token
            ]
            current_range, current = root_range, children
            for token in tokens:
                if isinstance(current, dict):
                    entry = current.get(token)
                elif isinstance(current, list) and token.isdigit():
                    index = int(token)
                    entry = current[index] if index < len(current) else None
                else:
                    return None
                if entry is None:
                    return None
                current_range, current = entry
            return current_range
        except (IndexError, KeyError, TypeError, ValueError, JSONDecodeError):
            return None
