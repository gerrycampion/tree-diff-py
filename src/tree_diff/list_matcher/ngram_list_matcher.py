from collections import Counter, defaultdict
from collections.abc import Iterable
from logging import getLogger
from typing import Any

from tree_diff.list_matcher.base_list_matcher import BaseListMatcher

logger = getLogger(__name__)


def _ngrams(text: str, n: int) -> Counter[str]:
    return (
        Counter({text: 1})
        if n == 0
        else Counter([text[i : i + n] for i in range(0, len(text) - n + 1)])
    )


def _add_ngrams(
    arr: Iterable[str],
    ngram_len: int,
    ngram_to_string: defaultdict[str, Counter[str]],
    string_to_ngram: dict[str, dict[str, Any]],
) -> None:
    for val in arr:
        counts = string_to_ngram.setdefault(
            val,
            {
                "ngrams": _ngrams(val, ngram_len),
                "i_match": set(),
                "match_me": set(),
            },
        )["ngrams"]
        for ngram, count in counts.items():
            ngram_to_string[ngram].update({val: count})


def _find_closest_matches(
    text: str,
    base_ngram_to_string: dict[str, Counter[str]],
    string_to_ngram: dict[str, dict[str, Any]],
) -> None:
    compare_counts = string_to_ngram[text]["ngrams"]
    scores: Counter[str] = Counter()
    for compare_ngram, compare_count in compare_counts.items():
        for base_string, base_count in base_ngram_to_string[compare_ngram].items():
            scores.update({base_string: min(compare_count, base_count)})
    if len(scores) > 0:
        most_common = scores.most_common()
        top = [t for t, count in most_common if count == most_common[0][1]]
        top = sorted(top, key=len)
        top = [t for t in top if len(t) == len(top[0])]
        string_to_ngram[text]["i_match"].update(top)
        for t in top:
            string_to_ngram[t]["match_me"].add(text)


def _remove(
    lst: set[str], string_to_ngram: dict[str, dict[str, Any]], item: str
) -> None:
    lst.remove(item)
    for match_me in string_to_ngram.get(item, {}).get("match_me", set()):
        string_to_ngram.get(match_me, {}).get("i_match", set()).discard(item)
    string_to_ngram.pop(item, None)


def _intersections(
    string_to_ngram: dict[str, dict[str, Any]],
    base: set[str],
    compare: set[str],
    pairs: list[tuple[str, str]],
    ngram_len: int,
) -> None:
    for base_item in list(base):
        compare_items = string_to_ngram[base_item]["i_match"]
        if len(compare_items) > 0:
            compare_items_that_have_base: list[str] = []
            compare_item_only_has_base = False
            for compare_item in compare_items:
                base_items = string_to_ngram[compare_item]["i_match"]
                if base_item in base_items:
                    compare_items_that_have_base.append(compare_item)
                    if len(base_items) == 1:
                        compare_item_only_has_base = True
            if compare_item_only_has_base and len(compare_items_that_have_base) == 1:
                compare_item = compare_items_that_have_base[0]
                pairs.append(
                    (
                        base_item,
                        compare_item,
                        #  "ngram_len": ngram_len
                    )
                )
                _remove(base, string_to_ngram, base_item)
                _remove(compare, string_to_ngram, compare_item)


def _match_lists(
    base: set[str],
    compare: set[str],
    pairs: list[tuple[str, str]],
    ngram_len: int,
    step: int,
) -> None:

    base_before = len(base)
    compare_before = len(compare)
    pairs_before = len(pairs)
    string_to_ngram: dict[str, dict[str, Any]] = {}
    base_ngram_to_string: defaultdict[str, Counter[str]] = defaultdict(
        lambda: Counter()
    )
    compare_ngram_to_string: defaultdict[str, Counter[str]] = defaultdict(
        lambda: Counter()
    )
    _add_ngrams(base, ngram_len, base_ngram_to_string, string_to_ngram)
    _add_ngrams(compare, ngram_len, compare_ngram_to_string, string_to_ngram)
    for c in compare:
        _find_closest_matches(c, base_ngram_to_string, string_to_ngram)
    for b in base:
        _find_closest_matches(b, compare_ngram_to_string, string_to_ngram)
    _intersections(string_to_ngram, base, compare, pairs, ngram_len)
    _intersections(string_to_ngram, compare, base, pairs, ngram_len)

    logger.debug(
        "%s, %s, %s->%s, %s->%s, %s->%s",
        step,
        ngram_len,
        base_before,
        len(base),
        compare_before,
        len(compare),
        pairs_before,
        len(pairs),
    )


def _max_len(base: Iterable[str], compare: Iterable[str]) -> int:
    values = [*base, *compare]
    return max(len(text) for text in values) if values else 0


def _decrement(num: int) -> int:
    # return int(num / 2) if num > 16 else num - 1
    return min(int(num / 2), 128) if num > 16 else num - 1


class NgramListMatcher(BaseListMatcher[str]):
    @staticmethod
    def match_lists(base: set[str], compare: set[str]) -> list[tuple[str, str]]:
        logger.debug("Step, Ngram, Base, Compare, Pairs")
        pairs: list[tuple[str, str]] = []
        step = 1
        _match_lists(base, compare, pairs, 0, step)
        ngram_length = _decrement(_max_len(base, compare))
        while ngram_length > 0 and base and compare:
            step += 1
            pairs_length = len(pairs)
            _match_lists(base, compare, pairs, ngram_length, step)
            if pairs_length == len(pairs):
                ngram_length = _decrement(min(ngram_length, _max_len(base, compare)))
        return pairs
