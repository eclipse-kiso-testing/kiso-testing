import pytest

from pykiso.tool.xray.xray_report import convert_test_status_to_xray_format, convert_time_to_xray_format, merge_results


def test_convert_time_to_xray_format():
    original_time = "25/12/21 15:30:45"
    expected_time = "2021-12-25T15:30:45+0000"
    assert convert_time_to_xray_format(original_time) == expected_time


def test_convert_time_to_xray_format_invalid_format():
    original_time = "2021-12-25 15:30:45"
    with pytest.raises(ValueError):
        convert_time_to_xray_format(original_time)


def test_convert_time_to_xray_format_edge_case():
    original_time = "01/01/70 00:00:00"
    expected_time = "1970-01-01T00:00:00+0000"
    assert convert_time_to_xray_format(original_time) == expected_time


@pytest.mark.parametrize("status,expected_status", ([True, "PASSED"], [False, "FAILED"]))
def test_convert_test_status_to_xray_format_passed(status, expected_status):
    assert convert_test_status_to_xray_format(status) == expected_status


def test_convert_test_status_to_xray_format_failed():
    assert convert_test_status_to_xray_format(False) == "FAILED"


def test_merge_results():
    test_results = [
        {
            "info": {"project": "PROJ1", "summary": "Test Summary 1"},
            "tests": [{"testKey": "TEST-1", "status": "PASSED"}],
        },
        {
            "info": {"project": "PROJ1", "summary": "Test Summary 1"},
            "tests": [{"testKey": "TEST-2", "status": "FAILED"}],
        },
        {
            "info": {"project": "PROJ2", "summary": "Test Summary 2"},
            "tests": [{"testKey": "TEST-3", "status": "PASSED"}],
        },
    ]

    expected_merged_results = [
        {
            "info": {"project": "PROJ1", "summary": "Test Summary 1"},
            "tests": [
                {"testKey": "TEST-1", "status": "PASSED"},
                {"testKey": "TEST-2", "status": "FAILED"},
            ],
        },
        {
            "info": {"project": "PROJ2", "summary": "Test Summary 2"},
            "tests": [{"testKey": "TEST-3", "status": "PASSED"}],
        },
    ]

    merged_results = merge_results(test_results)
    assert merged_results == expected_merged_results
