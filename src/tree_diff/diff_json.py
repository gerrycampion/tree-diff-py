from dataclasses import dataclass
from json import dumps
from logging import getLogger
from typing import Any

from tree_diff.base_list_matcher import BaseListMatcher

logger = getLogger(__name__)


@dataclass
class DiffNode:
    base: Any
    compare: Any
    base_pointer: str = ""
    compare_pointer: str = ""


def diff_value(
    list_matcher: type[BaseListMatcher[str]],
    diff_node: DiffNode,
) -> list[dict[str, Any]]:
    base, compare = diff_node.base, diff_node.compare
    scalars = {str, int, float, bool}
    objects = {dict}
    arrays = {list, tuple}
    if (
        base is None
        or compare is None
        or type(base) in scalars
        or type(compare) in scalars
        or type(base) is not type(compare)
    ):
        return diff_scalar(diff_node)
    if type(base) in objects and type(compare) in objects:
        return diff_obj(list_matcher, diff_node)
    if type(base) in arrays and type(compare) in arrays:
        return diff_array(list_matcher, diff_node)
    return []


def diff_scalar(diff_node: DiffNode) -> list[dict[str, Any]]:
    base, compare, base_pointer, compare_pointer = (
        diff_node.base,
        diff_node.compare,
        diff_node.base_pointer,
        diff_node.compare_pointer,
    )
    if base != compare:
        return [
            {
                "op": "replace",
                "path_base": base_pointer,
                "path_compare": compare_pointer,
                "value_base": base,
                "value_compare": compare,
            }
        ]
    return []


def diff_obj(
    list_matcher: type[BaseListMatcher[str]],
    diff_node: DiffNode,
) -> list[dict[str, Any]]:
    base, compare, base_pointer, compare_pointer = (
        diff_node.base,
        diff_node.compare,
        diff_node.base_pointer,
        diff_node.compare_pointer,
    )
    deletions: list[dict[str, Any]] = [
        {
            "op": "remove",
            "path_base": f"{base_pointer}/{k}",
            "path_compare": f"{compare_pointer}",
            "value_base": base[k],
        }
        for k in set(base.keys()) - set(compare.keys())
    ]
    additions: list[dict[str, Any]] = [
        {
            "op": "add",
            "path_base": f"{base_pointer}",
            "path_compare": f"{compare_pointer}/{k}",
            "value_compare": compare[k],
        }
        for k in set(compare.keys()) - set(base.keys())
    ]
    updates: list[dict[str, Any]] = []
    for k in set(base.keys()) & set(compare.keys()):
        updates.extend(
            diff_value(
                list_matcher,
                DiffNode(
                    base[k], compare[k], f"{base_pointer}/{k}", f"{compare_pointer}/{k}"
                ),
            )
        )
    return deletions + additions + updates


def diff_array(
    list_matcher: type[BaseListMatcher[str]],
    diff_node: DiffNode,
) -> list[dict[str, Any]]:
    base, compare, base_pointer, compare_pointer = (
        diff_node.base,
        diff_node.compare,
        diff_node.base_pointer,
        diff_node.compare_pointer,
    )
    json_to_base = _stringify(base)
    json_to_compare = _stringify(compare)
    json_base = set(json_to_base.keys())
    json_compare = set(json_to_compare.keys())
    logger.debug("=========== Matching Lists ============")
    logger.debug("Base: %s", base_pointer)
    logger.debug("Compare: %s", compare_pointer)
    pairs = list_matcher.match_lists(json_base, json_compare)
    deletions: list[dict[str, Any]] = [
        {
            "op": "remove",
            "path_base": f"{base_pointer}/{json_to_base[item][0]}",
            "path_compare": f"{compare_pointer}",
            "value_base": json_to_base[item][1],
        }
        for item in json_base
    ]
    additions: list[dict[str, Any]] = [
        {
            "op": "add",
            "path_base": f"{base_pointer}",
            "path_compare": f"{compare_pointer}/{json_to_compare[item][0]}",
            "value_compare": json_to_compare[item][1],
        }
        for item in json_compare
    ]
    updates: list[dict[str, Any]] = []
    moves: list[dict[str, str]] = []
    for base_item, comp_item in pairs:
        if json_to_base[base_item][0] != json_to_compare[comp_item][0]:
            moves.append(
                {
                    "op": "move",
                    "path_base": f"{base_pointer}/{json_to_base[base_item][0]}",
                    "path_compare": f"{compare_pointer}/{json_to_compare[comp_item][0]}",
                    "value_base": json_to_base[base_item][1],
                    "value_compare": json_to_compare[comp_item][1],
                }
            )
        updates.extend(
            diff_value(
                list_matcher,
                DiffNode(
                    json_to_base[base_item][1],
                    json_to_compare[comp_item][1],
                    f"{base_pointer}/{json_to_base[base_item][0]}",
                    f"{compare_pointer}/{json_to_compare[comp_item][0]}",
                ),
            )
        )
    return deletions + additions + moves + updates


def _stringify(json_list: list[Any] | tuple[Any, ...]) -> dict[str, tuple[int, Any]]:
    return {
        dumps(item, sort_keys=True, separators=(",", ":")): (index, item)
        for index, item in enumerate(json_list)
    }
