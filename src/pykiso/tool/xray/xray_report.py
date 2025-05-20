"""
Create the Xray dictionary from the junit test results
******************************************************

:module: xray_report

:synopsis: Provide the methods to send the test results report to the Xray REST API endpoint

..currentmodule:: xray_report

"""

from datetime import datetime, timedelta


def convert_test_status_to_xray_format(is_successful: bool) -> str:
    """Convert a boolean test result status to the corresponding XRAY format string.

    :param is_successful: The test result status. True if the test was successful, False otherwise.
    :return: "PASSED" if the test was successful, "FAILED" if the test was not.
    """
    match is_successful:
        case True:
            return "PASSED"
        case False:
            return "FAILED"


def merge_results(test_results: list[dict]) -> None:
    """
    Merges a list of test result dictionaries by combining test cases with the same info value.
    :param test_results: A list of dictionaries where each dictionary contains 'info' (a dictionary of test metadata)
        and 'tests' (a list of test cases).
    :return: A list of merged test result dictionaries. Each dictionary contains  info' (a dictionary of test metadata)
        and 'tests' (a combined list of test cases from all input dictionaries with the same 'info').
    """
    merged_results = []
    info_dict = {}

    for result in test_results:
        info = result["info"]
        info_key = tuple(sorted(info.items()))  # Convert dict to a tuple of sorted items to use as a key
        if info_key in info_dict:
            info_dict[info_key]["tests"].extend(result["tests"])
        else:
            new_entry = {"info": info, "tests": result["tests"]}
            info_dict[info_key] = new_entry
            merged_results.append(new_entry)

    return merged_results


def get_test_key_from_property(property: list) -> None | str:
    """
    Extracts the value of the "test_key" property from a list of property dictionaries.

    :param property: A list of dictionaries, where each dictionary represents a property
        with "name" and "value" keys.

    :return: None | str: The value of the "test_key" property if found, otherwise None.
    """
    test_key = None
    for p in property:
        if p["name"] == "test_key":
            test_key = p["value"]
            break
    return test_key


def compute_end_time(start_time: str, duration: float) -> str:
    """
    Computes the end time by adding a duration to a given start time.

    :param start_time: The start time in ISO 8601 format (e.g., "YYYY-MM-DDTHH:MM:SS").
        If the timezone offset is not provided, "+0000" (UTC) is assumed.
    :param duration: The duration in seconds to add to the start time.
    :return: The computed end time in ISO 8601 format with a "+0000" timezone offset.
    """
    if "+" not in start_time:
        start_time += "+0000"
    start_time_obj = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S+0000")
    end_time_obj = start_time_obj + timedelta(seconds=duration)
    return end_time_obj.replace(microsecond=0).isoformat() + "+0000"


def convert_time_to_xray_format(original_time: str) -> str:
    """
    Converts a given time string from the format "YYYY-MM-DDTHH:MM:SS" to the
    format "YYYY-MM-DDTHH:MM:SS+0000" by appending the UTC offset.

    :param original_time: The original time string in the format "YYYY-MM-DDTHH:MM:SS".
    :return: The converted time string in the format "YYYY-MM-DDTHH:MM:SS+0000".
    """
    if "+0000" not in original_time:
        return original_time + "+0000"
    return original_time


def create_result_dictionary(test_suites: dict, test_execution_summary: str | None = None) -> dict:
    """
    Processes test suite data and generates a dictionary containing information
    about the test execution and individual test cases for Xray integration.
    :param test_suites: A dictionary containing test suite data. Each test suite
            should include details such as errors, failures, time, timestamp, and
            test cases.
    :param test_execution_summary: the summary of the test execution ticket where to import the test results,
        if none is specified by default the test execution summary is "Xray test execution summary"

    :return: A dictionary with two keys:
            - "info": Contains metadata about the test execution, including summary,
              description, start date, finish date, and project key.
            - "tests": A list of dictionaries, each representing an individual test
              case with its test key, status, and comments.
    Notes:
        - The function assumes that the `testcase` field in the input can either be
          a single dictionary or a list of dictionaries. If it's a single dictionary,
          it is converted into a list for uniform processing.
        - The `properties` field of each test case is used to extract the test key.
        - The test execution status is determined based on the presence of failure
          or error logs.
        - The `convert_time_to_xray_format` and `compute_end_time` helper functions
          are used to calculate and format timestamps.
    """
    # filter xml file to keep only the info with properties
    xray_test_ticket = {}
    test_execution_ticket = {}
    xray_test_ticket_list = []

    for testsuite in test_suites:
        # all the testsuite -> build the test execution info
        has_errors = True if int(testsuite["errors"]) > 0 else False
        has_failures = True if int(testsuite["failures"]) > 0 else False
        duration = float(testsuite["time"])  # sec
        start_time = convert_time_to_xray_format(testsuite["timestamp"])  # str
        end_time = compute_end_time(start_time=start_time, duration=duration)  # str
        if test_execution_summary:
            summary = test_execution_summary
        else:
            summary = "Xray test execution summary"
        description = "Xray test execution description"

        test_execution_ticket = {
            "summary": summary,
            "description": description,
            "startDate": start_time,
            "finishDate": end_time,
        }

        if not isinstance(testsuite["testcase"], list):
            # if there is only one test case, it is not a list
            testcase = testsuite["testcase"]
            testsuite["testcase"] = [testcase]

        for testcase in testsuite["testcase"]:
            # for each test case -> build the xray test info
            name = testcase.get("name")
            if name == "test_run":
                continue

            # keep only test cases with a test_key in the decorator
            properties = testcase.get("properties")
            if properties is None:
                continue

            test_key = get_test_key_from_property(properties["property"])
            duration = float(testcase["time"])  # sec
            start_time = convert_time_to_xray_format(testcase["timestamp"])
            end_time = compute_end_time(start_time=start_time, duration=duration)
            # get failure or error logs
            failure_logs = testcase.get("failure")
            error_logs = testcase.get("error")
            # get the test status
            is_failed = True if failure_logs and has_failures else False
            is_error = True if error_logs and has_errors else False
            if is_failed:
                comment = failure_logs["#text"]
            elif is_error:
                comment = error_logs["#text"]
            elif failure_logs == error_logs:
                comment = "Successful execution"
            else:
                raise ValueError("Test should has failed or passed. Not both.")
            status = "PASSED" if not is_failed and not is_error else "FAILED"

            xray_test_ticket = {
                "testKey": test_key,
                "comment": name + ": " + comment,
                "status": status,
            }
            xray_test_ticket_list.append(xray_test_ticket)

    # update project key
    project_key = xray_test_ticket["testKey"].split("-")[0]
    test_execution_ticket["project"] = project_key
    return {"info": test_execution_ticket, "tests": xray_test_ticket_list}


def is_parameterized_test(test_results: dict) -> bool:
    """
    Check if the test is parameterized. The test is parametrized if several times there are the same test_key.
    :param test_results: The test results to check.

    :return: True if the test is parameterized, False otherwise.
    """
    test_keys_list = [test["testKey"] for test in test_results["tests"]]  # Extract all test keys
    test_keys_set = {test["testKey"] for test in test_results["tests"]}  # Extract unique test keys
    return len(test_keys_list) != len(test_keys_set)


def reformat_xml_results(test_results: dict, test_execution_key: str | None = None) -> list[dict]:
    """
    Reformats a list of XML results dictionaries by merging them based on their 'testKey' key.

    :param test_results: A list of dictionaries where each dictionary contains 'info' (a dictionary of test metadata)
        and 'tests' (a list of test cases).
    :param test_execution_key: the xray's test execution ticket key where to import the test results,
        if none is specified a new test execution ticket will be created

    :return: A list of merged test result dictionaries. Each dictionary contains 'info' (a dictionary of test metadata)
        and 'tests' (a combined list of test cases from all input dictionaries with the same 'info').
    """
    test_execution_ticket = test_results["info"]
    if is_parameterized_test(test_results=test_results):
        xray_test_ticket_new = merge_test_results_comments(test_results["tests"])
        parameterized_test_results = {"info": test_execution_ticket, "tests": xray_test_ticket_new}
        if test_execution_key is not None:
            parameterized_test_results["testExecutionKey"] = test_execution_key
        return [parameterized_test_results]
    else:
        if test_execution_key is not None:
            test_results["testExecutionKey"] = test_execution_key
        return [test_results]


def merge_test_results_comments(test_results: list) -> list:
    """
    Merges test results with the same test key by combining their comments and determining the overall status.

    :param test_results: A list of dictionaries where each dictionary represents a test result.
        Each test result dictionary should have the following keys:
        - "testKey" (str): The unique identifier for the test.
        - "comment" (str): A comment associated with the test result.
        - "status" (str): The status of the test, either "PASSED" or "FAILED".
    :return: A list of merged test result dictionaries. Each dictionary contains:
        - "testKey" (str): The unique identifier for the test.
        - "comment" (str): The combined comments for all test results with the same test key.
        - "status" (str): The overall status for the test key, which is "FAILED" if any test with the same key has a status of "FAILED", otherwise "PASSED".
    """
    merged_results = {}
    for test in test_results:
        test_key = test["testKey"]
        if test_key not in merged_results:
            merged_results[test_key] = {"testKey": test_key, "comment": "", "status": "PASSED"}
        # Append the comment
        if merged_results[test_key]["comment"]:
            merged_results[test_key]["comment"] += "\n"
        merged_results[test_key]["comment"] += test["comment"]

        # Update the status to FAILED if any test with the same testKey has FAILED
        if test["status"] == "FAILED":
            merged_results[test_key]["status"] = "FAILED"

    # Convert the merged results back to a list
    return list(merged_results.values())
