import sys
from json import dumps, loads
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tree_diff import (  # noqa: E402
    CSVMapping,  # noqa: E402
    JSONMapping,  # noqa: E402
    NgramListMatcher,
    TreeMappingFactory,
    XMLMapping,  # noqa: E402
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


def test_xml_diff_add_uses_enclosing_element_for_missing_side():
    diffs = diff_xml(
        NgramListMatcher,
        "<root><tags><tag>A</tag></tags></root>",
        "<root><tags><tag>A</tag><tag>B</tag></tags></root>",
    )

    assert diffs == [
        {
            "op": "add",
            "path_base": "/root/tags[1]",
            "path_compare": "/root/tags[1]/tag[2]",
            "value_compare": {"#text": "B"},
        }
    ]


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


def test_json_path_to_range_locates_nested_value():
    source = '{"nested":{"items":["first","second"]}}'
    start = source.index('"second"')

    assert JSONMapping().path_to_range(source, "/nested/items/1") == (
        start,
        start + len('"second"'),
    )


def test_path_to_range_uses_utf16_offsets_for_ace():
    source = '{"emoji":"😀","target":1}'
    start = len(source[: source.index("1")].encode("utf-16-le")) // 2

    assert JSONMapping().path_to_range(source, "/target") == (start, start + 1)


def test_xml_path_to_range_locates_attribute_and_text():
    source = '<root><item id="a">First</item><item id="b">Second</item></root>'
    mapping = XMLMapping()

    assert mapping.path_to_range(source, "/root/item[2]/@id") == (
        source.index('"b"'),
        source.index('"b"') + 3,
    )
    assert mapping.path_to_range(source, "/root/item[2]/text()") == (
        source.index("Second"),
        source.index("Second") + len("Second"),
    )


def test_csv_path_to_range_locates_quoted_cell():
    source = 'name,value\nalpha,"two, words"\n'
    start = source.index('"two, words"')

    assert CSVMapping().path_to_range(source, "1,value") == (
        start,
        start + len('"two, words"'),
    )


def test_csv_path_to_range_empty_selects_entire_table():
    source = "id\n1\n😀\n"

    assert CSVMapping().path_to_range(source, "") == (
        0,
        len(source.encode("utf-16-le")) // 2,
    )


def test_csv_path_to_range_preserves_bom_offsets_and_escaped_headers():
    source = '\ufeff"name","a""b"\nalpha,1\n'
    start = source.index('"a""b"')

    assert CSVMapping().path_to_range(source, 'a"b') == (
        start,
        start + len('"a""b"'),
    )
