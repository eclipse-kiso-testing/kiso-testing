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


@pytest.mark.parametrize("status,expected_status", ([True, "PASSED"], [False, "FAILED"]))
def test_convert_test_status_to_xray_format_passed(status, expected_status):
    assert convert_test_status_to_xray_format(status) == expected_status


def test_convert_test_status_to_xray_format_failed():
    assert convert_test_status_to_xray_format(False) == "FAILED"


def test_convert_time_to_xray_format_with_missing_timezone():
    original_time = "2023-01-01T12:00:00"
    expected_time = "2023-01-01T12:00:00+0000"
    assert convert_time_to_xray_format(original_time) == expected_time


def test_convert_time_to_xray_format_with_existing_timezone():
    original_time = "2023-01-01T12:00:00+0000"
    expected_time = "2023-01-01T12:00:00+0000"
    assert convert_time_to_xray_format(original_time) == expected_time


def test_convert_time_to_xray_format_with_invalid_format():
    original_time = "2023-01-01 12:00:00"  # Missing 'T' separator
    expected_time = "2023-01-01 12:00:00+0000"
    assert convert_time_to_xray_format(original_time) == expected_time


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

    assert create_result_dictionary(test_suites, jira_keys=["TEST-1"]) == expected_result


def test_create_result_dictionary_with_jira_keys():
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
        },
        {
            "errors": "0",
            "failures": "0",
            "time": "10.5",
            "timestamp": "2023-01-01T12:00:00",
            "testcase": {
                "name": "test_case_2",
                "time": "10.5",
                "timestamp": "2023-01-01T12:00:00",
                "properties": {"property": [{"name": "test_key", "value": "TEST-2"}]},
            },
        },
    ]

    expected_result = {
        "info": {
            "startDate": "2023-01-01T12:00:00+0000",
            "finishDate": "2023-01-01T12:00:10+0000",
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
                "comment": "test_case_2: Successful execution",
                "status": "PASSED",
            },
        ],
    }

    assert create_result_dictionary(test_suites, jira_keys=["TEST-1", "TEST-2"]) == expected_result


def test_create_result_dictionary_without_jira_keys():
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

    assert (
        create_result_dictionary(
            test_suites,
            jira_keys=[],
        )
        == expected_result
    )


def test_create_result_dictionary_with_single_testcase_with_test_execution_summary():
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
            "summary": "Ticket summary",
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

    assert create_result_dictionary(test_suites, ["TEST-1"], "Ticket summary") == expected_result


def test_create_result_dictionary_with_single_testcase_with_test_execution_description():
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
            "description": "Ticket description",
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

    assert (
        create_result_dictionary(test_suites, ["TEST-1"], test_execution_description="Ticket description")
        == expected_result
    )


def test_create_result_dictionary_with_single_testcase_with_test_execution_summary_and_test_execution_description():
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
            "description": "Ticket description",
            "summary": "Ticket summary",
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

    assert (
        create_result_dictionary(
            test_suites,
            jira_keys=["TEST-1"],
            test_execution_summary="Ticket summary",
            test_execution_description="Ticket description",
        )
        == expected_result
    )


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
            "summary": "Ticket with multiple test cases",
            "description": "Ticket description with multiple test cases",
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

    assert (
        create_result_dictionary(
            test_suites,
            jira_keys=["TEST-1", "TEST-2"],
            test_execution_description="Ticket description with multiple test cases",
            test_execution_summary="Ticket with multiple test cases",
        )
        == expected_result
    )


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

    assert (
        create_result_dictionary(
            test_suites,
            jira_keys=["TEST-1"],
            test_execution_summary="Xray test execution summary",
            test_execution_description="Xray test execution description",
        )
        == expected_result
    )


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
    test_execution_key = None

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

    result = reformat_xml_results(test_results, test_execution_key)
    assert result == expected_result


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
    test_execution_key = "ABC-123"

    expected_result = [
        {
            "info": {
                "summary": "Test Execution Summary",
                "description": "Test Execution Description",
                "startDate": "2023-01-01T12:00:00+0000",
                "finishDate": "2023-01-01T12:30:00+0000",
                "project": "TEST",
            },
            "testExecutionKey": "ABC-123",
            "tests": [
                {
                    "testKey": "TEST-1",
                    "comment": "test_case_1: Successful execution\ntest_case_2: Traceback error",
                    "status": "FAILED",
                },
            ],
        },
    ]

    result = reformat_xml_results(test_results, test_execution_key)
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
    test_execution_key = "TEST-EXEC-123"

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

    result = reformat_xml_results(test_results, test_execution_key)
    assert result == expected_result


def test_create_result_dictionary_with_none_properties():
    """Test create_result_dictionary when testcase has properties=None - should skip the testcase."""
    test_suites = [
        {
            "errors": "0",
            "failures": "0",
            "time": "1800",  # 30 minutes
            "timestamp": "2023-01-01T12:00:00",
            "testcase": [
                {
                    "name": "test_case_with_properties",
                    "time": "900",
                    "timestamp": "2023-01-01T12:00:00",
                    "properties": {"property": [{"name": "test_key", "value": "TEST-1"}]},
                },
                {
                    "name": "test_case_without_properties",
                    "time": "900",
                    "timestamp": "2023-01-01T12:15:00",
                    "properties": None,  # This testcase should be skipped
                },
            ],
        }
    ]

    jira_keys = []

    result = create_result_dictionary(test_suites, jira_keys)

    # Only the testcase with properties should be included
    expected_result = {
        "info": {
            "startDate": "2023-01-01T12:00:00+0000",
            "finishDate": "2023-01-01T12:30:00+0000",
            "project": "TEST",
        },
        "tests": [
            {"testKey": "TEST-1", "comment": "test_case_with_properties: Successful execution", "status": "PASSED"}
        ],
    }

    assert result == expected_result
    # Verify that only one test is included (the one with properties)
    assert len(result["tests"]) == 1
    assert result["tests"][0]["testKey"] == "TEST-1"


def test_create_result_dictionary_with_test_key_not_in_jira_keys():
    """Test create_result_dictionary when test_key is not in jira_keys list - should skip the testcase."""
    test_suites = [
        {
            "errors": "0",
            "failures": "0",
            "time": "1800",  # 30 minutes
            "timestamp": "2023-01-01T12:00:00",
            "testcase": [
                {
                    "name": "test_case_in_jira_keys",
                    "time": "900",
                    "timestamp": "2023-01-01T12:00:00",
                    "properties": {"property": [{"name": "test_key", "value": "TEST-1"}]},
                },
                {
                    "name": "test_case_not_in_jira_keys",
                    "time": "900",
                    "timestamp": "2023-01-01T12:15:00",
                    "properties": {"property": [{"name": "test_key", "value": "TEST-999"}]},  # Not in jira_keys
                },
                {
                    "name": "test_case_also_in_jira_keys",
                    "time": "900",
                    "timestamp": "2023-01-01T12:30:00",
                    "properties": {"property": [{"name": "test_key", "value": "TEST-2"}]},
                },
            ],
        }
    ]

    # Only TEST-1 and TEST-2 are in the jira_keys list, TEST-999 should be skipped
    jira_keys = ["TEST-1", "TEST-2"]

    result = create_result_dictionary(test_suites, jira_keys)

    # Only the testcases with test keys in jira_keys should be included
    expected_result = {
        "info": {
            "startDate": "2023-01-01T12:00:00+0000",
            "finishDate": "2023-01-01T12:30:00+0000",
            "project": "TEST",
        },
        "tests": [
            {"testKey": "TEST-1", "comment": "test_case_in_jira_keys: Successful execution", "status": "PASSED"},
            {"testKey": "TEST-2", "comment": "test_case_also_in_jira_keys: Successful execution", "status": "PASSED"},
        ],
    }

    assert result == expected_result
    # Verify that only two tests are included (the ones with test keys in jira_keys)
    assert len(result["tests"]) == 2
    assert result["tests"][0]["testKey"] == "TEST-1"
    assert result["tests"][1]["testKey"] == "TEST-2"
    # Verify that TEST-999 is not included
    test_keys_in_result = [test["testKey"] for test in result["tests"]]
    assert "TEST-999" not in test_keys_in_result
