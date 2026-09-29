from dataclasses import dataclass
from json import dumps
from logging import getLogger
from typing import Any

from tree_diff.base_list_matcher import BaseListMatcher
from tree_diff.tree import TreeMapping, TreeNode

logger = getLogger(__name__)


@dataclass
class TreeDiffContext:
    base: TreeNode
    compare: TreeNode
    base_path: str = ""
    compare_path: str = ""


def diff_tree(
    list_matcher: type[BaseListMatcher[str]],
    context: TreeDiffContext,
    mapping: TreeMapping,
) -> list[dict[str, Any]]:
    base, compare = context.base, context.compare
    if base.kind != compare.kind or base.kind == "scalar":
        return _diff_scalar(context)
    if base.kind == "object":
        return _diff_object(list_matcher, context, mapping)
    return _diff_array(list_matcher, context, mapping)


def _diff_scalar(context: TreeDiffContext) -> list[dict[str, Any]]:
    base, compare = context.base, context.compare
    base_value, compare_value = base.to_value(), compare.to_value()
    if base_value == compare_value and type(base_value) is type(compare_value):
        return []
    return [
        {
            "op": "replace",
            "path_base": context.base_path,
            "path_compare": context.compare_path,
            "value_base": base_value,
            "value_compare": compare_value,
        }
    ]


def _diff_object(
    list_matcher: type[BaseListMatcher[str]],
    context: TreeDiffContext,
    mapping: TreeMapping,
) -> list[dict[str, Any]]:
    base, compare = context.base, context.compare
    base_path, compare_path = context.base_path, context.compare_path
    if not isinstance(base.children, dict) or not isinstance(compare.children, dict):
        raise TypeError("Object nodes must have mapping children")
    base_children = base.children
    compare_children = compare.children
    deletions = [
        {
            "op": "remove",
            "path_base": mapping.child_path(base_path, base, key),
            "path_compare": compare_path,
            "value_base": base_children[key].to_value(),
        }
        for key in base_children.keys() - compare_children.keys()
    ]
    additions = [
        {
            "op": "add",
            "path_base": base_path,
            "path_compare": mapping.child_path(compare_path, compare, key),
            "value_compare": compare_children[key].to_value(),
        }
        for key in compare_children.keys() - base_children.keys()
    ]
    updates: list[dict[str, Any]] = []
    for key in base_children.keys() & compare_children.keys():
        updates.extend(
            diff_tree(
                list_matcher,
                TreeDiffContext(
                    base_children[key],
                    compare_children[key],
                    mapping.child_path(base_path, base, key),
                    mapping.child_path(compare_path, compare, key),
                ),
                mapping,
            )
        )
    return deletions + additions + updates


def _diff_array(
    list_matcher: type[BaseListMatcher[str]],
    context: TreeDiffContext,
    mapping: TreeMapping,
) -> list[dict[str, Any]]:
    base, compare = context.base, context.compare
    base_path, compare_path = context.base_path, context.compare_path
    if not isinstance(base.children, list) or not isinstance(compare.children, list):
        raise TypeError("Array nodes must have list children")
    base_children = base.children
    compare_children = compare.children
    stringified_base = _stringify(base_children)
    stringified_compare = _stringify(compare_children)
    base_keys, compare_keys = set(stringified_base), set(stringified_compare)
    logger.debug("=========== Matching Lists ============")
    logger.debug("Base: %s", base_path)
    logger.debug("Compare: %s", compare_path)
    pairs = list_matcher.match_lists(base_keys, compare_keys)

    deletions = [
        {
            "op": "remove",
            "path_base": mapping.child_path(
                base_path,
                base,
                str(stringified_base[item][0]),
            ),
            "path_compare": mapping.array_parent_path(compare_path, compare),
            "value_base": stringified_base[item][1].to_value(),
        }
        for item in base_keys
    ]
    additions = [
        {
            "op": "add",
            "path_base": mapping.array_parent_path(base_path, base),
            "path_compare": mapping.child_path(
                compare_path,
                compare,
                str(stringified_compare[item][0]),
            ),
            "value_compare": stringified_compare[item][1].to_value(),
        }
        for item in compare_keys
    ]
    updates: list[dict[str, Any]] = []
    moves: list[dict[str, Any]] = []
    for base_item, compare_item in pairs:
        base_index, base_node = stringified_base[base_item]
        compare_index, compare_node = stringified_compare[compare_item]
        base_item_path = mapping.child_path(base_path, base, str(base_index))
        compare_item_path = mapping.child_path(
            compare_path, compare, str(compare_index)
        )
        if base_index != compare_index:
            moves.append(
                {
                    "op": "move",
                    "path_base": base_item_path,
                    "path_compare": compare_item_path,
                    "value_base": base_node.to_value(),
                    "value_compare": compare_node.to_value(),
                }
            )
        updates.extend(
            diff_tree(
                list_matcher,
                TreeDiffContext(
                    base_node, compare_node, base_item_path, compare_item_path
                ),
                mapping,
            )
        )
    return deletions + additions + moves + updates


def _stringify(children: list[TreeNode]) -> dict[str, tuple[int, TreeNode]]:
    return {
        dumps(child.to_value(), sort_keys=True, separators=(",", ":")): (index, child)
        for index, child in enumerate(children)
    }
