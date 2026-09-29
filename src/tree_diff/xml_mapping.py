from collections import defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from tree_diff.tree import TreeMapping, TreeNode


class XMLMapping(TreeMapping):
    FILE_EXTENSION = ".xml"

    @classmethod
    def load_from_file(
        cls, filename: str | Path
    ) -> ElementTree.ElementTree[ElementTree.Element]:
        return ElementTree.parse(filename)

    def to_tree(self, value: Any) -> TreeNode:
        if isinstance(value, ElementTree.ElementTree):
            root = value.getroot()
        elif isinstance(value, ElementTree.Element):
            root = value
        elif isinstance(value, Path):
            root = ElementTree.parse(value).getroot()
        elif isinstance(value, str):
            root = ElementTree.fromstring(value)
        else:
            raise TypeError("XML input must be XML text, a Path, or an Element")
        return TreeNode("object", children={root.tag: self._element_to_tree(root)})

    def _element_to_tree(self, element: ElementTree.Element) -> TreeNode:
        children: dict[str, TreeNode] = {
            f"@{key}": TreeNode("scalar", value=value)
            for key, value in element.attrib.items()
        }
        text = (element.text or "").strip()
        if text:
            children["#text"] = TreeNode("scalar", value=text)

        grouped: dict[str, list[TreeNode]] = defaultdict(list)
        for child in element:
            grouped[child.tag].append(self._element_to_tree(child))
        for tag, elements in grouped.items():
            children[tag] = TreeNode("array", children=elements, segment=tag)
        return TreeNode("object", children=children)

    def child_path(self, path: str, parent: TreeNode, key: str) -> str:
        if parent.kind == "array":
            return f"{path}[{int(key) + 1}]"
        if key.startswith("@"):
            return f"{path}/@{key[1:]}"
        if key == "#text":
            return f"{path}/text()"
        return f"{path}/{key}"
