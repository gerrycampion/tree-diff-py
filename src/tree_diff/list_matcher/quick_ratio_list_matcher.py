from collections import defaultdict
from difflib import SequenceMatcher
from itertools import product
from typing import Any

from tree_diff import each_deep
from tree_diff.list_matcher.base_list_matcher import BaseListMatcher


def _post_order_list(tree: Any) -> list[dict[str, Any]]:
    lst: list[dict[str, Any]] = []
    each_deep(
        node=tree,
        after=lambda context, path, indexed_path: lst.append(
            {"node": context[-1], "path": path, "indexed_path": indexed_path}
        ),
    )
    return lst


def _append_if_str(context: list[Any], lst: list[str]) -> None:
    if isinstance(context[-1], str):
        lst.append(context[-1])


def _all_values(tree: Any) -> list[str]:
    lst: list[str] = []
    each_deep(
        node=tree,
        after=lambda context, path, indexed_path: _append_if_str(context, lst),
    )
    return lst


def _diff_score(base_node: dict[str, Any], compare_node: dict[str, Any]) -> float:
    base = base_node["node"]
    compare = compare_node["node"]
    if isinstance(base, str) and isinstance(compare, str):
        return _diff_str(base, compare)
    return 0.0


def _diff_scores(base: Any, compare: Any) -> dict[str, list[dict[str, Any]]]:
    base_nodes = _post_order_list(base)
    compare_nodes = _post_order_list(compare)
    node_levels: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"base_nodes": [], "compare_nodes": []}
    )
    for base_node in base_nodes:
        node_levels[base_node["path"]]["base_nodes"].append(base_node)
    for compare_node in compare_nodes:
        node_levels[compare_node["path"]]["compare_nodes"].append(compare_node)
    scores: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path, level in node_levels.items():
        for base_node, compare_node in product(
            level["base_nodes"], level["compare_nodes"]
        ):
            scores[path].append(
                {
                    "base_node": base_node,
                    "compare_node": compare_node,
                    "score": _diff_score(base_node, compare_node),
                }
            )
    for level in node_levels.values():
        for node in level["base_nodes"] + level["compare_nodes"]:
            del node["node"]
    return scores


def _diff_str(base_node: str, compare_node: str) -> float:
    # return 100 if base_node == compare_node else 0
    """
    Where T is the total number of elements in both sequences,
    and M is the number of matches,
    this is 2.0*M / T.
    Note that this is 1.0 if the sequences are identical,
    and 0.0 if they have nothing in common.
    """
    return SequenceMatcher(
        None,
        base_node,
        compare_node,
        False,
    ).quick_ratio()


class QRListMatcher(BaseListMatcher[str]):
    @staticmethod
    def match_lists(base: set[str], compare: set[str]) -> list[tuple[str, str]]:
        scores: list[dict[str, Any]] = []
        for base_node, compare_node in product(base, compare):
            score = _diff_str(base_node, compare_node)
            scores.append({"score": score, "base": base_node, "comp": compare_node})
        pairs: list[tuple[str, str]] = []
        for score in sorted(scores, key=lambda score: score["score"], reverse=True):
            if score["base"] in base and score["comp"] in compare:
                pairs.append((score["base"], score["comp"]))
                base.remove(score["base"])
                compare.remove(score["comp"])
        return pairs
