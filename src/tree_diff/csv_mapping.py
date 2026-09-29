import csv
from io import StringIO
from pathlib import Path
from typing import Any

from tree_diff.tree import TreeMapping, TreeNode


def _escape_path_segment(segment: str) -> str:
    return segment.replace("\\", "\\\\").replace(",", "\\,")


class CSVMapping(TreeMapping):
    FILE_EXTENSION = ".csv"

    @classmethod
    def load_from_file(cls, filename: str | Path) -> list[list[str]]:
        with open(filename, encoding="utf-8-sig", newline="") as source:
            return list(csv.reader(source))

    def to_tree(self, value: Any) -> TreeNode:
        if isinstance(value, Path):
            records = self.load_from_file(value)
        elif isinstance(value, str):
            text = value.removeprefix("\ufeff")
            records = list(csv.reader(StringIO(text, newline="")))
        elif isinstance(value, list):
            records = value
        else:
            raise TypeError("CSV input must be records, CSV text, or a Path")
        if not records:
            return TreeNode(
                "object",
                children={
                    "columns": TreeNode("array", children=[]),
                    "row": TreeNode("array", children=[], segment="row"),
                },
            )

        headers = records[0]
        if len(headers) != len(set(headers)):
            raise ValueError("CSV column names must be unique")

        rows: list[TreeNode] = []
        for row_number, values in enumerate(records[1:], start=2):
            if len(values) != len(headers):
                raise ValueError(
                    f"CSV row {row_number} has {len(values)} fields; "
                    f"expected {len(headers)}"
                )
            rows.append(
                TreeNode(
                    "object",
                    children={
                        header: TreeNode("scalar", value=value)
                        for header, value in zip(headers, values, strict=True)
                    },
                )
            )
        return TreeNode(
            "object",
            children={
                "columns": TreeNode(
                    "array",
                    children=[TreeNode("scalar", value=header) for header in headers],
                    segment="columns",
                ),
                "row": TreeNode("array", children=rows, segment="row"),
            },
        )

    def child_path(self, path: str, parent: TreeNode, key: str) -> str:
        if parent.kind == "array":
            if not isinstance(parent.children, list):
                raise TypeError("Array nodes must have list children")
            index = int(key)
            if parent.segment == "row":
                return str(index + 1)
            if parent.segment == "columns":
                return _escape_path_segment(str(parent.children[index].to_value()))
            raise ValueError(f"Unknown CSV array segment: {parent.segment!r}")
        if not path:
            return ""
        return f"{path},{_escape_path_segment(key)}"
