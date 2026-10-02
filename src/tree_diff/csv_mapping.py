import csv
from io import StringIO
from pathlib import Path
from typing import Any

from tree_diff.tree import SourceRange, TreeMapping, TreeNode


def _escape_path_segment(segment: str) -> str:
    return segment.replace("\\", "\\\\").replace(",", "\\,")


def _csv_records(source: str) -> list[list[SourceRange]]:
    records: list[list[SourceRange]] = []
    row: list[SourceRange] = []
    field_start = 1 if source.startswith("\ufeff") else 0
    cursor = field_start
    in_quotes = False
    while cursor < len(source):
        character = source[cursor]
        if character == '"':
            if in_quotes and cursor + 1 < len(source) and source[cursor + 1] == '"':
                cursor += 2
                continue
            in_quotes = not in_quotes
        elif not in_quotes and character == ",":
            row.append((field_start, cursor))
            field_start = cursor + 1
        elif not in_quotes and character in "\r\n":
            row.append((field_start, cursor))
            records.append(row)
            row = []
            cursor += 1
            if character == "\r" and cursor < len(source) and source[cursor] == "\n":
                cursor += 1
            field_start = cursor
            continue
        cursor += 1
    if field_start < len(source) or row or (source and source[-1] not in "\r\n"):
        row.append((field_start, len(source)))
        records.append(row)
    return records


def _split_csv_path(path: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    escaped = False
    for character in path:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ",":
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    parts.append("".join(current))
    return parts


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

    def _path_to_range(self, source: str, path: str) -> SourceRange | None:
        if not path:
            return 0, len(source)
        records = _csv_records(source)
        if not records:
            return None
        headers = []
        for start, end in records[0]:
            header = source[start:end]
            if len(header) >= 2 and header[0] == '"' and header[-1] == '"':
                header = header[1:-1].replace('""', '"')
            headers.append(header)
        parts = _split_csv_path(path)
        if len(parts) == 1:
            if parts[0] in headers:
                return records[0][headers.index(parts[0])]
            if parts[0].isdigit():
                row_index = int(parts[0])
                if 1 <= row_index < len(records):
                    return records[row_index][0][0], records[row_index][-1][1]
            return None
        if len(parts) == 2 and parts[0].isdigit():
            row_index = int(parts[0])
            if 1 <= row_index < len(records) and parts[1] in headers:
                return records[row_index][headers.index(parts[1])]
        return None
