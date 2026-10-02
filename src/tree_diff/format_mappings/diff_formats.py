from pathlib import Path
from typing import Any

from tree_diff import (
    TreeDiffContext,
    diff_tree,
)
from tree_diff.format_mappings.csv_mapping import CSVMapping
from tree_diff.format_mappings.json_mapping import JSONMapping
from tree_diff.format_mappings.tree import TreeMapping
from tree_diff.format_mappings.xml_mapping import XMLMapping
from tree_diff.list_matcher.base_list_matcher import BaseListMatcher


class TreeMappingFactory:
    _mapping_types: tuple[type[TreeMapping], ...] = (
        JSONMapping,
        XMLMapping,
        CSVMapping,
    )

    @classmethod
    def create(cls, filename: str | Path) -> TreeMapping:
        extension = Path(filename).suffix.lower()
        for mapping_type in cls._mapping_types:
            if extension == mapping_type.FILE_EXTENSION:
                return mapping_type()
        supported = ", ".join(
            mapping_type.FILE_EXTENSION for mapping_type in cls._mapping_types
        )
        raise ValueError(
            f"Unsupported file extension {extension!r}; "
            f"supported extensions: {supported}"
        )


def _diff_mapped(
    list_matcher: type[BaseListMatcher[str]],
    base: Any,
    compare: Any,
    mapping: TreeMapping,
) -> list[dict[str, Any]]:
    return diff_tree(
        list_matcher,
        TreeDiffContext(mapping.to_tree(base), mapping.to_tree(compare)),
        mapping,
    )


def diff_json(
    list_matcher: type[BaseListMatcher[str]], base_json: Any, compare_json: Any
) -> list[dict[str, Any]]:
    return _diff_mapped(list_matcher, base_json, compare_json, JSONMapping())


def diff_xml(
    list_matcher: type[BaseListMatcher[str]], base_xml: Any, compare_xml: Any
) -> list[dict[str, Any]]:
    return _diff_mapped(list_matcher, base_xml, compare_xml, XMLMapping())


def diff_csv(
    list_matcher: type[BaseListMatcher[str]], base_csv: Any, compare_csv: Any
) -> list[dict[str, Any]]:
    return _diff_mapped(list_matcher, base_csv, compare_csv, CSVMapping())


def diff_files(
    list_matcher: type[BaseListMatcher[str]],
    base_filename: str | Path,
    compare_filename: str | Path,
) -> list[dict[str, Any]]:
    base_mapping = TreeMappingFactory.create(base_filename)
    compare_mapping = TreeMappingFactory.create(compare_filename)
    if type(base_mapping) is not type(compare_mapping):
        raise ValueError("Base and compare files must have the same format")
    base = base_mapping.load_from_file(base_filename)
    compare = compare_mapping.load_from_file(compare_filename)
    return _diff_mapped(list_matcher, base, compare, base_mapping)
