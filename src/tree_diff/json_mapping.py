from json import load as load_json
from pathlib import Path
from typing import Any

from tree_diff.tree import TreeMapping, TreeNode


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
