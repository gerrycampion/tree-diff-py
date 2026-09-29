import sys
from json import dumps, loads
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tree_diff import (  # noqa: E402
    NgramListMatcher,
    TreeMappingFactory,
    diff_csv,
    diff_files,
    diff_json,
    diff_xml,
)

SAMPLES_DIR = ROOT / "samples"


@pytest.mark.parametrize(
    ("format_name", "extension"),
    [("json", ".json"), ("xml", ".xml"), ("csv", ".csv")],
)
def test_samples_match_generated_diffs(format_name, extension):
    base_file = SAMPLES_DIR / format_name / f"base{extension}"
    compare_file = SAMPLES_DIR / format_name / f"compare{extension}"
    mapping = TreeMappingFactory.create(base_file)
    assert mapping.FILE_EXTENSION == extension

    generated = sorted(
        diff_files(NgramListMatcher, base_file, compare_file),
        key=lambda diff: dumps(diff, sort_keys=True, separators=(",", ":")),
    )
    detailed = loads(
        (SAMPLES_DIR / format_name / "diff_detailed.json").read_text(encoding="utf-8")
    )
    paths = [
        {key: diff[key] for key in ("op", "path_base", "path_compare")}
        for diff in generated
    ]

    assert generated == detailed
    assert paths == loads(
        (SAMPLES_DIR / format_name / "diff_paths.json").read_text(encoding="utf-8")
    )
    assert paths == loads(
        (SAMPLES_DIR / format_name / "diff_summary.json").read_text(encoding="utf-8")
    )


def test_xml_diff_uses_xpath_style_paths():
    diffs = diff_xml(
        NgramListMatcher,
        '<catalog version="1"/>',
        '<catalog version="2"/>',
    )

    assert diffs == [
        {
            "op": "replace",
            "path_base": "/catalog/@version",
            "path_compare": "/catalog/@version",
            "value_base": "1",
            "value_compare": "2",
        }
    ]


def test_xml_diff_indexes_repeated_siblings():
    diffs = diff_xml(
        NgramListMatcher,
        "<root><item>A</item><item>B</item></root>",
        "<root><item>B</item><item>A</item></root>",
    )

    assert {
        (diff["path_base"], diff["path_compare"])
        for diff in diffs
        if diff["op"] == "move"
    } == {
        ("/root/item[1]", "/root/item[2]"),
        ("/root/item[2]", "/root/item[1]"),
    }


def test_csv_diff_uses_row_and_column_paths():
    diffs = diff_csv(
        NgramListMatcher,
        "id,value\n1,alpha\n",
        "id,value\n1,bravo\n",
    )

    assert diffs == [
        {
            "op": "replace",
            "path_base": "1,value",
            "path_compare": "1,value",
            "value_base": "alpha",
            "value_compare": "bravo",
        }
    ]


def test_csv_diff_reports_header_only_changes():
    diffs = diff_csv(NgramListMatcher, "name\n", "title\n")

    assert diffs == [
        {
            "op": "replace",
            "path_base": "name",
            "path_compare": "title",
            "value_base": "name",
            "value_compare": "title",
        }
    ]


def test_csv_diff_uses_document_and_row_paths():
    added = diff_csv(NgramListMatcher, "id\n1\n", "id\n1\n2\n")
    removed = diff_csv(NgramListMatcher, "id\n1\n2\n", "id\n1\n")

    assert [
        (diff["op"], diff["path_base"], diff["path_compare"]) for diff in added
    ] == [("add", "", "2")]
    assert [
        (diff["op"], diff["path_base"], diff["path_compare"]) for diff in removed
    ] == [("remove", "2", "")]


def test_json_mapping_escapes_json_pointer_segments():
    diffs = diff_json(
        NgramListMatcher,
        {"a/b~c": 1},
        {"a/b~c": 2},
    )

    assert diffs[0]["path_base"] == "/a~1b~0c"
    assert diffs[0]["path_compare"] == "/a~1b~0c"
