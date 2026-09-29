"""tree-diff-py package."""

from .base_list_matcher import BaseListMatcher
from .csv_mapping import CSVMapping
from .diff_formats import TreeMappingFactory, diff_csv, diff_files, diff_json, diff_xml
from .diff_tree import TreeDiffContext, diff_tree
from .report import save_to_file
from .json_mapping import JSONMapping
from .ngram_list_matcher import NgramListMatcher
from .quick_ratio_list_matcher import QRListMatcher
from .tree import TreeMapping, TreeNode
from .xml_mapping import XMLMapping

__all__ = [
    "BaseListMatcher",
    "CSVMapping",
    "JSONMapping",
    "NgramListMatcher",
    "QRListMatcher",
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
