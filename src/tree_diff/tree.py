from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Literal

NodeKind = Literal["array", "object", "scalar"]


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
