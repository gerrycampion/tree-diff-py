import re
from collections import defaultdict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from tree_diff.tree import SourceRange, TreeMapping, TreeNode


def _xml_markup_end(source: str, start: int) -> int:
    quote = ""
    cursor = start + 1
    while cursor < len(source):
        character = source[cursor]
        if quote:
            if character == quote:
                quote = ""
        elif character in "\"'":
            quote = character
        elif character == ">":
            return cursor + 1
        cursor += 1
    return len(source)


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

    def _path_to_range(self, source: str, path: str) -> SourceRange | None:
        if not path.startswith("/"):
            return None
        parts = path[1:].split("/")
        if not parts or not parts[0]:
            return None
        special = None
        if parts[-1] == "text()":
            special = "text"
            parts.pop()
        elif parts[-1].startswith("@"):
            special = parts.pop()[1:]

        root: dict[str, Any] | None = None
        stack: list[dict[str, Any]] = []
        cursor = 0
        while cursor < len(source):
            tag_start = source.find("<", cursor)
            if tag_start < 0:
                break
            if stack and stack[-1]["text"] is None and tag_start > cursor:
                stack[-1]["text"] = (cursor, tag_start)
            if source.startswith("<!--", tag_start):
                close = source.find("-->", tag_start + 4)
                cursor = len(source) if close < 0 else close + 3
                continue
            if source.startswith("<![CDATA[", tag_start):
                close = source.find("]]>", tag_start + 9)
                if stack and stack[-1]["text"] is None and close >= 0:
                    stack[-1]["text"] = (tag_start + 9, close)
                cursor = len(source) if close < 0 else close + 3
                continue
            tag_end = _xml_markup_end(source, tag_start)
            markup = source[tag_start:tag_end]
            cursor = tag_end
            if markup.startswith("<?") or markup.startswith("<!"):
                continue
            if markup.startswith("</"):
                if stack:
                    stack.pop()["end"] = tag_end
                continue

            name_match = re.match(r"<([^\s/>]+)", markup)
            if not name_match:
                continue
            name = name_match.group(1)
            attributes: dict[str, SourceRange] = {}
            offset = name_match.end()
            while offset < len(markup):
                attribute_match = re.match(
                    r"\s+([^\s=/>]+)\s*=\s*(['\"])", markup[offset:]
                )
                if not attribute_match:
                    break
                attribute_name = attribute_match.group(1)
                quote = attribute_match.group(2)
                value_start = offset + attribute_match.end()
                value_end = markup.find(quote, value_start)
                if value_end < 0:
                    break
                attributes[attribute_name] = (
                    tag_start + value_start - 1,
                    tag_start + value_end + 1,
                )
                offset = value_end + 1

            node: dict[str, Any] = {
                "name": name,
                "start": tag_start,
                "end": tag_end,
                "attributes": attributes,
                "text": None,
                "children": [],
            }
            if stack:
                stack[-1]["children"].append(node)
            else:
                root = node
            if not markup.rstrip().endswith("/>"):
                stack.append(node)

        if root is None:
            return None

        segment_match = re.fullmatch(r"(.*?)(?:\[(\d+)\])?", parts[0])
        if not segment_match or segment_match.group(1) != root["name"]:
            return None
        node = root
        for part in parts[1:]:
            segment_match = re.fullmatch(r"(.*?)(?:\[(\d+)\])?", part)
            if not segment_match:
                return None
            name = segment_match.group(1)
            index = int(segment_match.group(2) or "1") - 1
            matching = [child for child in node["children"] if child["name"] == name]
            if index < 0 or index >= len(matching):
                return None
            node = matching[index]

        if special == "text":
            text_range = node["text"]
            if text_range is None:
                return None
            start, end = text_range
            while start < end and source[start].isspace():
                start += 1
            while end > start and source[end - 1].isspace():
                end -= 1
            return start, end
        if special is not None:
            return node["attributes"].get(special)
        return node["start"], node["end"]
