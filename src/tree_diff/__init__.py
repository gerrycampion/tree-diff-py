"""tree-diff-py package."""

from .diff_tree import TreeDiffContext, diff_tree
from .format_mappings.csv_mapping import CSVMapping
from .format_mappings.diff_formats import (
    TreeMappingFactory,
    diff_csv,
    diff_files,
    diff_json,
    diff_xml,
)
from .format_mappings.json_mapping import JSONMapping
from .format_mappings.tree import SourceRange, TreeMapping, TreeNode
from .format_mappings.xml_mapping import XMLMapping
from .list_matcher.base_list_matcher import BaseListMatcher
from .list_matcher.ngram_list_matcher import NgramListMatcher
from .list_matcher.quick_ratio_list_matcher import QRListMatcher
from .report import save_to_file

__all__ = [
    "BaseListMatcher",
    "CSVMapping",
    "JSONMapping",
    "NgramListMatcher",
    "QRListMatcher",
    "SourceRange",
    "TreeMapping",
    "TreeMappingFactory",
    "TreeDiffContext",
    "TreeNode",
    "XMLMapping",
    "diff_csv",
    "diff_files",
    "diff_json",
    "diff_tree",
    "diff_xml",
    "save_to_file",
]

__version__ = "0.1.0"
