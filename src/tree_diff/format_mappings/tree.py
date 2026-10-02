from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Literal, TypeAlias

NodeKind = Literal["array", "object", "scalar"]
SourceRange: TypeAlias = tuple[int, int]


def to_utf16_range(source: str, source_range: SourceRange | None) -> SourceRange | None:
    if source_range is None:
        return None
    return tuple(
        len(source[:offset].encode("utf-16-le")) // 2 for offset in source_range
    )


@dataclass
class TreeNode:
    kind: NodeKind
    value: Any = None
    children: dict[str, "TreeNode"] | list["TreeNode"] | None = None
    segment: str | None = None

    def to_value(self) -> Any:
        if self.kind == "object":
            return {key: child.to_value() for key, child in self.children.items()}
        if self.kind == "array":
            return [child.to_value() for child in self.children]
        return self.value


class TreeMapping(ABC):
    FILE_EXTENSION: ClassVar[str]

    @classmethod
    @abstractmethod
    def load_from_file(cls, filename: str | Path) -> Any:
        raise NotImplementedError

    @abstractmethod
    def to_tree(self, value: Any) -> TreeNode:
        raise NotImplementedError

    @abstractmethod
    def child_path(self, path: str, parent: TreeNode, key: str) -> str:
        raise NotImplementedError

    def array_parent_path(self, path: str, parent: TreeNode) -> str:
        return path

    def path_to_range(self, source: str, path: str) -> SourceRange | None:
        """Return a zero-based, end-exclusive UTF-16 range for a diff path."""
        return to_utf16_range(source, self._path_to_range(source, path))

    @abstractmethod
    def _path_to_range(self, source: str, path: str) -> SourceRange | None:
        """Return a zero-based, end-exclusive Python string range."""
        raise NotImplementedError
