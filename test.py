import logging
import os
from json import dumps
from os.path import join
from typing import Any

from tree_diff.diff_formats import diff_files
from tree_diff.ngram_list_matcher import NgramListMatcher
from tree_diff.report import save_to_file

base_filename: str = os.environ.get("BASE_FILENAME", "")
compare_filename: str = os.environ.get("COMPARE_FILENAME", "")
output_directory: str = os.environ.get("OUTPUT_DIRECTORY", "")
log_level_name: str = os.environ.get("LOG_LEVEL", "WARNING").upper()
log_level = getattr(logging, log_level_name, None)
if not isinstance(log_level, int):
    raise ValueError(
        "LOG_LEVEL must be a valid Python logging level, e.g. DEBUG, INFO, WARNING, ERROR."
    )

logging.basicConfig(level=log_level, format="%(levelname)s:%(name)s:%(message)s")

if not base_filename or not compare_filename or not output_directory:
    raise ValueError(
        "Set BASE_FILENAME, COMPARE_FILENAME, and OUTPUT_DIRECTORY in .env or the environment."
    )

diffs: list[dict[str, Any]] = sorted(
    diff_files(NgramListMatcher, base_filename, compare_filename),
    key=lambda diff: dumps(diff, sort_keys=True, separators=(",", ":")),
)


save_to_file(
    diffs,
    join(output_directory, "diff_paths.json"),
    keep=["diffs", "op", "path_base", "path_compare"],
)
save_to_file(
    diffs,
    join(output_directory, "diff_summary.json"),
    keep=["diffs", "op", "path_base", "path_compare"],
)
save_to_file(
    diffs,
    join(output_directory, "diff_detailed.json"),
    keep=["diffs", "op", "path_base", "path_compare", "value_base", "value_compare"],
)


# base_values = set(all_values(base))
# compare_values = set(all_values(compare))
# pairs = pair_arrays(base_values, compare_values)

# save_to_file(
#     {
#         "pairs": sorted(
#             [pair for pair in pairs if pair[0] != pair[1]],
#             key=lambda pair: pair[0],
#         ),
#         "base": sorted([*base_values]),
#         "comp": sorted([*compare_values]),
#     },
#     f"{out_dir}pairs_halves.json",
# )


# 3055, 61-3072, 68-3081, 63-3081, 59-3112

# scores = diff_scores(base, compare)
# save_to_file(scores, f"{out_dir}out.json")


# pair_arrays_quick_ratio(base_values, compare_values)
