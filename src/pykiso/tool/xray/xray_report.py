"""
Create the Xray dictionary from the test result reports
*******************************************************

:module: xray_report

:synopsis: Provide the methods to send the test results report to the Xray REST API endpoint

..currentmodule:: xray_report

"""

from collections import OrderedDict
from datetime import datetime


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


def convert_time_to_xray_format(original_time: str) -> str:
    """
    Converts a given time string from the format "dd/mm/yy HH:MM:SS" to the
    format "YYYY-MM-DDTHH:MM:SS+0000" suitable for Xray.

    :param original_time: The original time string in the format "dd/mm/yy HH:MM:SS".
    :return: The converted time string in the format "YYYY-MM-DDTHH:MM:SS+0000".
    """
    converted_time = datetime.strptime(original_time, "%d/%m/%y %H:%M:%S")
    return converted_time.strftime("%Y-%m-%dT%H:%M:%S+0000")


def create_result_dictionary(  # noqa: C901 # TODO: reduce complexity
    test_execution_results: dict[str, OrderedDict], test_execution_id: None = None
) -> list[dict]:
    xray_result_dictionaries = []
    collected_test_results = []

    # collect only the test_list and the time_results information
    for test_results in test_execution_results.values():
        for key in test_results.keys():
            tmp_dict = {}
            if key == "test_list":
                tmp_dict["test_list"] = test_results["test_list"]
            elif key == "time_result":
                tmp_dict["time_result"] = test_results["time_result"]
            if len(tmp_dict) > 0:
                collected_test_results.append(tmp_dict)

    # build the xray result list with all the test results dictionaries
    for test_result in collected_test_results:
        if test_result.get("time_result") is not None:
            start_time = test_result["time_result"]["Start Time"]
            finish_date = test_result["time_result"]["End Time"]
        for key in test_result.keys():
            xray_dict = {
                "info": {},
                "tests": [],
            }
            if key == "test_list":
                for test_steps_name in test_result[key].keys():
                    # test_steps_name= setUp, test_1, tearDown, test_run
                    for step_list in test_result[key][test_steps_name].get("steps"):
                        for step in step_list:
                            test_dict = {}
                            if step["is_parameterized"]:
                                # create one test execution ticket per parameterized test
                                if "test_key" in step.get("properties", {}):  # has a test_key
                                    # xray test ticket
                                    test_dict = {
                                        "testKey": step["properties"]["test_key"],
                                        "comment": step["failure_log"],  # step["description"]
                                        "status": convert_test_status_to_xray_format(step["succeed"]),
                                    }

                                    # xray test execution ticket
                                    info_dict = {
                                        "project": step["properties"]["test_key"].split("-")[0],
                                        "summary": test_steps_name + " " + step["test_name_function"],
                                        "description": step["description"],
                                        # for all the test, should be per test function
                                        "startDate": convert_time_to_xray_format(start_time),
                                        "finishDate": convert_time_to_xray_format(finish_date),
                                    }
                                    xray_dict = {"info": info_dict, "tests": [test_dict]}
                                    # to send the test results to an existing test execution ticket
                                    if test_execution_id is not None:
                                        xray_dict["testExecutionKey"] = test_execution_id
                                    if len(xray_dict) == 0:
                                        continue
                                    xray_result_dictionaries.append(xray_dict)

                            if not step["is_parameterized"]:
                                # create one common test execution for all the tests
                                if "test_key" in step.get("properties", {}):  # has a test_key
                                    info_dict = {
                                        "project": step["properties"]["test_key"].split("-")[0],
                                        "summary": "Execution of the manual tests",
                                        "description": "Description",
                                        # for running all the tests
                                        "startDate": convert_time_to_xray_format(start_time),
                                        "finishDate": convert_time_to_xray_format(finish_date),
                                    }
                                    test_dict = {
                                        "testKey": step["properties"]["test_key"],
                                        "comment": step["failure_log"],  # step["description"]
                                        "status": convert_test_status_to_xray_format(step["succeed"]),
                                    }
                                    xray_dict = {"info": info_dict, "tests": [test_dict]}
                                    # to send the test results to an existing test execution ticket
                                    if test_execution_id is not None:
                                        xray_dict["testExecutionKey"] = test_execution_id
                                    xray_result_dictionaries.append(xray_dict)
    return xray_result_dictionaries


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
