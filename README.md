# tree-diff-py

Utilities for diffing tree-like (JSON, XML) and tabular (CSV) data and matching list items.

## Installation

```bash
pip install tree-diff-py
```

## Development

```bash
python -m pip install --upgrade pip
python -m pip install --editable ".[dev]"
pre-commit install
```

## How it works

The library maps each supported input format to a shared tree representation, then
uses one recursive diff algorithm for all formats. Format mappings define how their
paths are written.

### 1. Recursive value diffing

The main algorithm walks the base and compares values in parallel. It handles:

- scalar values like strings, numbers, booleans, and nulls
- object keys and nested object paths
- arrays and list items

When the values are the same type, it compares them recursively. If the type changes or the scalar value changes, it records a replace operation with the source and target paths.

For example:

```json
{
  "status": "draft"
}
```

versus

```json
{
  "status": "published"
}
```

produces:

```json
[
  {
    "op": "replace",
    "path_base": "/status",
    "path_compare": "/status",
    "value_base": "draft",
    "value_compare": "published"
  }
]
```

### 2. Object-level changes

Object diffs are produced by comparing keys. A key that exists only in the base is treated as a remove. A key that exists only in the compare is treated as an add. Shared keys keep descending into the nested values.

Example:

```json
{
  "owner": { "name": "Alex", "team": "platform" }
}
```

versus

```json
{
  "owner": { "name": "Alex", "team": "platform-ops" }
}
```

yields a replace on `/owner/team`.

### 3. Array matching with n-gram similarity

The key challenge is list comparison. Arrays are frequently reordered, and a naive diff would mark every item as removed and re-added. This project uses an n-gram based matcher to find the closest matching items even when list order changes.

The matcher:

- converts each item into a string representation
- builds n-grams from those strings
- compares n-gram overlap across base and compare lists
- picks the strongest candidate matches
- resolves one-to-one item pairing before generating move or replace operations

This makes it good at detecting changes like:

- reordered tags or teams
- similar feature entries with updated metadata
- same item moved to a different index with small changes

Example:

```json
[
  "urgent",
  "backend",
  "release",
  "api"
]
```

versus

```json
[
  "backend",
  "release",
  "urgent",
  "api",
  "security"
]
```

The diff records list moves and the added item `"security"` instead of treating the entire array as completely different.

### 4. Example from the sample data

The sample files in `samples/json/base.json` and `samples/json/compare.json` demonstrate several common cases:

- scalar change: `status` from `draft` to `published`
- nested field change: `owner.team` from `platform` to `platform-ops`
- moved list items: `tags` and `teams` are reordered
- matched object updates: `search` and `billing` entries are paired by similarity even when indices shift
- added item: `security` appears in the compare list
- removed item: a nested feature appears in the base but not in the compare

The XML and CSV equivalents are in `samples/xml/` and `samples/csv/`. Each format
directory contains `base`, `compare`, and its `diff_paths.json`, `diff_summary.json`,
and `diff_detailed.json` outputs.

A typical output looks like:

```json
[
  {"op": "move", "path_base": "/tags/0", "path_compare": "/tags/2"},
  {"op": "move", "path_base": "/features/1", "path_compare": "/features/2"},
  {"op": "replace", "path_base": "/status", "path_compare": "/status"},
  {"op": "add", "path_base": "/tags", "path_compare": "/tags/4"}
]
```

## Example usage

```python
import json
from pathlib import Path

from tree_diff import NgramListMatcher, diff_json

base = json.loads(Path("samples/json/base.json").read_text())
compare = json.loads(Path("samples/json/compare.json").read_text())

diffs = diff_json(NgramListMatcher, base, compare)
print(diffs)
```

This will return a sequence of diff records describing the semantic changes between the two JSON structures.

## XML and CSV

`diff_xml` accepts XML text, an `xml.etree.ElementTree` element/tree, or a `Path` to
an XML file. It maps elements, attributes, and trimmed direct text into the shared
tree. Repeated sibling elements are matched as lists. Paths use XPath-style element
and attribute segments, such as `/catalog/item[2]/@id` and
`/catalog/item[1]/text()`.

`diff_csv` accepts CSV text or a `Path` to a CSV file. The first record supplies
column names and each subsequent record is a row; cell values remain strings.
Column names must be unique and each row must have the header's field count. CSV
paths use `r,c`, where `r` is the one-based row number and `c` is the column name.
A whole row is addressed by `r`; the whole document has an empty path. Header changes
use the affected column name as the path.

```python
from pathlib import Path

from tree_diff import NgramListMatcher, diff_csv, diff_xml

xml_diffs = diff_xml(
    NgramListMatcher,
    "<catalog><item id='a'>First</item></catalog>",
    "<catalog><item id='a'>Updated</item></catalog>",
)
csv_diffs = diff_csv(
    NgramListMatcher,
    Path("before.csv"),
    Path("after.csv"),
)
```

`diff_json`, `diff_xml`, and `diff_csv` are format-specific entry points over the
same tree diff engine. JSON paths use JSON Pointer escaping.
Each mapping also implements `path_to_range(source, path)`, returning zero-based,
end-exclusive UTF-16 source offsets using that format's path syntax, matching Ace's
editor coordinates.

For file inputs, `diff_files` selects the mapping from each filename extension and
loads each file using that mapping's loader. Both files must use the same format.

```python
from tree_diff import NgramListMatcher, diff_files

diffs = diff_files(
    NgramListMatcher,
    "samples/xml/base.xml",
    "samples/xml/compare.xml",
)
```

## Runtime performance

The implementation is designed to prioritize semantics over raw text diffing. In practice, runtime depends on the size and shape of the data, but the core behavior is:

- recursive traversal of the object tree is linear in the number of nodes visited
- object comparison is dominated by key-set operations and nested recursion
- list matching is the expensive part for large arrays because each item is compared using n-gram overlap and candidate matching

### Big-O view

Let:

- $N$ be the total number of scalar/object/array nodes in the JSON tree
- $K$ be the number of keys in an object
- $L$ be the number of items in a list
- $M$ be the average string length of list items
- $G$ be the n-gram size used for matching

For the recursive diff engine, the worst-case cost is roughly:

$$
O(N)
$$

for a tree walk when the structure is mostly nested but not recomputed excessively. Object comparisons are effectively bounded by key comparisons and recursive descent, so they remain proportional to the total visited nodes.

For the n-gram list matcher, the cost is higher because it builds a set of n-grams for each candidate item and compares overlaps across the arrays. The matching stage has a practical complexity closer to:

$$
O(L^2 \cdot M)
$$

in the worst case, because each candidate item may be compared against many others while scoring shared n-grams, and each comparison may touch strings of length $M$.

If the list length is $L$ and each string has length $M$, then building the n-gram index is roughly:

$$
O(L \cdot M)
$$

and the candidate scoring can grow toward quadratic behavior in the list size.

The exact constant factors depend on the n-gram length $G$, the number of unique n-grams, and how many candidate matches survive early filtering. In real runs, it is usually closer to a “many small list comparisons” problem than a pure $O(L^2)$ worst-case scenario, but it is still the main cost driver for large arrays.

### Adaptive n-gram sizing

The list matcher does not use a single fixed n-gram size for the whole run. It starts with a relatively large n-gram length to find obvious matches quickly and then decreases the window size as the remaining unmatched items get smaller and harder to distinguish.

The current implementation reduces the n-gram size with a logarithmic-style step:

```python
return min(int(num / 2), 128) if num > 16 else num - 1
```

This means that when the list is large, the matcher shrinks the n-gram size aggressively at first, then more gently as it approaches smaller windows. The effect is:

- coarse matching early: large n-grams catch strong similarities and avoid false matches due to small shared substrings
- finer matching later: once most obvious pairs are resolved, smaller n-grams help distinguish near-duplicates and leftover candidates
- stable convergence: eventually the matcher reaches a point where nearly all remaining pairs can be resolved with a tighter window

This adaptive behavior is useful for lists where many entries are similar but not identical. A single, fixed n-gram length can be too coarse for subtle differences or too narrow to find the right matches when the strings are highly similar but shifted. By decreasing size gradually, the algorithm gets strong matches early and then refines them only where needed.

For example, consider two lists of feature names or configuration labels where the majority of items are very similar:

- initial large n-grams match broad structural similarity and place items into likely candidate groups
- smaller n-grams then separate near-duplicates that share a common base name but differ in a suffix or parameter value
- once most pairs are matched, only a few ambiguous leftovers remain, and the smaller window resolves them precisely

This is one reason the list matcher works well for reordered or slightly edited JSON arrays without reverting to a brittle index-only comparison.

### Why the n-gram matcher is worth it

The n-gram matcher is intentionally more expensive than a simple index-based comparison, but it is much better when arrays contain similar items that have been reordered or when list order is not a good proxy for identity. In other words, the algorithm trades additional CPU for more meaningful matches in real-world JSON payloads.

This is best suited to:

- configuration files and manifests
- API payloads with nested objects and small-to-medium arrays
- scenarios where list reordering is common but item identity should remain stable

It becomes less ideal for very large arrays with highly unique items or for extremely large payloads where a faster, less semantic diff is acceptable.

For small to medium JSON structures, the cost is usually low and the better match quality is worth it. For large datasets, it is best to keep arrays moderate and to scope diffs to the relevant object subsets when possible.
