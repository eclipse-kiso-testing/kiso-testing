import pytest

from pykiso.tool.xray.xray_report import (
    compute_end_time,
    convert_test_status_to_xray_format,
    convert_time_to_xray_format,
    create_result_dictionary,
    get_test_key_from_property,
    is_parameterized_test,
    merge_results,
    reformat_xml_results,
)


def test_convert_time_to_xray_format():
    original_time = "2021-12-25T15:30:45"
    expected_time = "2021-12-25T15:30:45+0000"
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


def test_get_test_key_from_property_with_valid_property():
    properties = [
        {"name": "test_key", "value": "TEST-123"},
        {"name": "other_key", "value": "OTHER-456"},
    ]
    assert get_test_key_from_property(properties) == "TEST-123"


def test_get_test_key_from_property_with_missing_test_key():
    properties = [
        {"name": "other_key", "value": "OTHER-456"},
        {"name": "another_key", "value": "ANOTHER-789"},
    ]
    assert get_test_key_from_property(properties) is None


def test_compute_end_time_with_valid_input():
    start_time = "2023-01-01T12:00:00"
    duration = 3600  # 1 hour in seconds
    expected_end_time = "2023-01-01T13:00:00+0000"
    assert compute_end_time(start_time, duration) == expected_end_time


def test_compute_end_time_with_timezone_in_start_time():
    start_time = "2023-01-01T12:00:00+0000"
    duration = 1800  # 30 minutes in seconds
    expected_end_time = "2023-01-01T12:30:00+0000"
    assert compute_end_time(start_time, duration) == expected_end_time


def test_compute_end_time_with_zero_duration():
    start_time = "2023-01-01T12:00:00"
    duration = 0  # No duration
    expected_end_time = "2023-01-01T12:00:00+0000"
    assert compute_end_time(start_time, duration) == expected_end_time


def test_compute_end_time_with_invalid_start_time_format():
    start_time = "2023-01-01 12:00:00"  # Invalid format
    duration = 3600
    with pytest.raises(ValueError):
        compute_end_time(start_time, duration)


def test_create_result_dictionary_with_single_testcase():
    test_suites = [
        {
            "errors": "0",
            "failures": "0",
            "time": "10.5",
            "timestamp": "2023-01-01T12:00:00",
            "testcase": {
                "name": "test_case_1",
                "time": "10.5",
                "timestamp": "2023-01-01T12:00:00",
                "properties": {"property": [{"name": "test_key", "value": "TEST-1"}]},
            },
        }
    ]

    expected_result = {
        "info": {
            "summary": "Xray test execution summary",
            "description": "Xray test execution description",
            "startDate": "2023-01-01T12:00:00+0000",
            "finishDate": "2023-01-01T12:00:10+0000",
            "project": "TEST",
        },
        "tests": [
            {
                "testKey": "TEST-1",
                "comment": "test_case_1: Successful execution",
                "status": "PASSED",
            }
        ],
    }

    assert create_result_dictionary(test_suites) == expected_result


def test_create_result_dictionary_with_multiple_testcases():
    test_suites = [
        {
            "errors": "0",
            "failures": "1",
            "time": "20.0",
            "timestamp": "2023-01-01T12:00:00",
            "testcase": [
                {
                    "name": "test_case_1",
                    "time": "10.0",
                    "timestamp": "2023-01-01T12:00:00",
                    "properties": {"property": [{"name": "test_key", "value": "TEST-1"}]},
                },
                {
                    "name": "test_case_2",
                    "time": "10.0",
                    "timestamp": "2023-01-01T12:10:00",
                    "properties": {"property": [{"name": "test_key", "value": "TEST-2"}]},
                    "failure": {"#text": "Test failed due to an error."},
                },
            ],
        }
    ]

    expected_result = {
        "info": {
            "summary": "Xray test execution summary",
            "description": "Xray test execution description",
            "startDate": "2023-01-01T12:00:00+0000",
            "finishDate": "2023-01-01T12:00:20+0000",
            "project": "TEST",
        },
        "tests": [
            {
                "testKey": "TEST-1",
                "comment": "test_case_1: Successful execution",
                "status": "PASSED",
            },
            {
                "testKey": "TEST-2",
                "comment": "test_case_2: Test failed due to an error.",
                "status": "FAILED",
            },
        ],
    }

    assert create_result_dictionary(test_suites) == expected_result


def test_create_result_dictionary_with_missing_properties():
    test_suites = [
        {
            "errors": "0",
            "failures": "0",
            "time": "5.0",
            "timestamp": "2023-01-01T12:00:00",
            "testcase": {
                "name": "test_case_1",
                "time": "5.0",
                "timestamp": "2023-01-01T12:00:00",
            },
        }
    ]

    with pytest.raises(KeyError):
        create_result_dictionary(test_suites)


def test_create_result_dictionary_with_error_logs():
    test_suites = [
        {
            "errors": "1",
            "failures": "0",
            "time": "15.0",
            "timestamp": "2023-01-01T12:00:00",
            "testcase": {
                "name": "test_case_1",
                "time": "15.0",
                "timestamp": "2023-01-01T12:00:00",
                "properties": {"property": [{"name": "test_key", "value": "TEST-1"}]},
                "error": {"#text": "An unexpected error occurred."},
            },
        }
    ]

    expected_result = {
        "info": {
            "summary": "Xray test execution summary",
            "description": "Xray test execution description",
            "startDate": "2023-01-01T12:00:00+0000",
            "finishDate": "2023-01-01T12:00:15+0000",
            "project": "TEST",
        },
        "tests": [
            {
                "testKey": "TEST-1",
                "comment": "test_case_1: An unexpected error occurred.",
                "status": "FAILED",
            }
        ],
    }

    assert create_result_dictionary(test_suites) == expected_result


def test_is_parameterized_test_with_non_parameterized_tests():
    test_results = {
        "tests": [
            {"testKey": "TEST-1", "status": "PASSED"},
            {"testKey": "TEST-2", "status": "FAILED"},
            {"testKey": "TEST-3", "status": "PASSED"},
        ]
    }
    assert not is_parameterized_test(test_results)


def test_is_parameterized_test_with_parameterized_tests():
    test_results = {
        "tests": [
            {"testKey": "TEST-1", "status": "PASSED"},
            {"testKey": "TEST-1", "status": "FAILED"},
            {"testKey": "TEST-2", "status": "PASSED"},
        ]
    }
    assert is_parameterized_test(test_results)


def test_is_parameterized_test_with_empty_tests():
    test_results = {"tests": []}
    assert not is_parameterized_test(test_results)


def test_is_parameterized_test_with_single_test():
    test_results = {"tests": [{"testKey": "TEST-1", "status": "PASSED"}]}
    assert not is_parameterized_test(test_results)


def test_reformat_xml_results_with_parameterized_tests():
    test_results = {
        "info": {
            "summary": "Test Execution Summary",
            "description": "Test Execution Description",
            "startDate": "2023-01-01T12:00:00+0000",
            "finishDate": "2023-01-01T12:30:00+0000",
            "project": "TEST",
        },
        "tests": [
            {"testKey": "TEST-1", "comment": "test_case_1: Successful execution", "status": "PASSED"},
            {"testKey": "TEST-1", "comment": "test_case_2: Traceback error", "status": "FAILED"},
        ],
    }
    test_execution_id = None

    expected_result = [
        {
            "info": {
                "summary": "Test Execution Summary",
                "description": "Test Execution Description",
                "startDate": "2023-01-01T12:00:00+0000",
                "finishDate": "2023-01-01T12:30:00+0000",
                "project": "TEST",
            },
            "tests": [
                {
                    "testKey": "TEST-1",
                    "comment": "test_case_1: Successful execution\ntest_case_2: Traceback error",
                    "status": "FAILED",
                },
            ],
        },
    ]

    result = reformat_xml_results(test_results, test_execution_id)
    assert result == expected_result


def test_reformat_xml_results_with_non_parameterized_tests():
    test_results = {
        "info": {
            "summary": "Test Execution Summary",
            "description": "Test Execution Description",
            "startDate": "2023-01-01T12:00:00+0000",
            "finishDate": "2023-01-01T12:30:00+0000",
            "project": "TEST",
        },
        "tests": [
            {"testKey": "TEST-1", "comment": "test_case_1: Successful execution", "status": "PASSED"},
            {"testKey": "TEST-2", "comment": "test_case_2: Failed execution", "status": "FAILED"},
        ],
    }
    test_execution_id = "TEST-EXEC-123"

    expected_result = [
        {
            "info": {
                "summary": "Test Execution Summary",
                "description": "Test Execution Description",
                "startDate": "2023-01-01T12:00:00+0000",
                "finishDate": "2023-01-01T12:30:00+0000",
                "project": "TEST",
            },
            "tests": [
                {"testKey": "TEST-1", "comment": "test_case_1: Successful execution", "status": "PASSED"},
                {"testKey": "TEST-2", "comment": "test_case_2: Failed execution", "status": "FAILED"},
            ],
            "testExecutionKey": "TEST-EXEC-123",
        }
    ]

    result = reformat_xml_results(test_results, test_execution_id)
    assert result == expected_result
