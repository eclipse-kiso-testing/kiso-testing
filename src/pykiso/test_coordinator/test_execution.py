##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Execution of tests
******************

:module: test_execution

:synopsis: Execute a test environment based on the supplied configuration.

.. currentmodule:: test_execute

.. note::
    1. Glob a list of test-suite folders
    2. Generate a list of test-suites with a list of test-cases
    3. Loop per suite
    4. Gather result
"""
from __future__ import annotations

import functools
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union
from unittest import util
from unittest.loader import VALID_MODULE_NAME

from pykiso.test_result.multi_result import MultiTestResult

if TYPE_CHECKING:
    from ..lib.connectors.cc_pcan_can import CCPCanCan
    from ..lib.connectors.cc_socket_can.cc_socket_can import CCSocketCan
    from ..types import ConfigDict, SuiteConfig
    from .test_case import BasicTest

import enum
import logging
import re
import time
import unittest
from collections import OrderedDict, namedtuple
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path

import xmlrunner

import pykiso

from ..exceptions import AuxiliaryCreationError, TestCollectionError
from ..logging_initializer import get_logging_options
from ..test_result.assert_step_report import StepReportData, assert_decorator, generate_step_report
from ..test_result.text_result import BannerTestResult, ResultStream
from ..test_result.xml_result import XmlTestResult
from . import test_suite

log = logging.getLogger(__name__)

TestFilterPattern = namedtuple("TestFilterPattern", "test_file, test_class, test_case")


@enum.unique
class ExitCode(enum.IntEnum):
    """List of possible exit codes"""

    ALL_TESTS_SUCCEEDED = 0
    ONE_OR_MORE_TESTS_FAILED = 1
    ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION = 2
    ONE_OR_MORE_TESTS_FAILED_AND_RAISED_UNEXPECTED_EXCEPTION = 3
    AUXILIARY_CREATION_FAILED = 4
    BAD_CLI_USAGE = 5
    UNRESOLVED_THREADS = 6


def create_test_suite(
    test_suite_dict: SuiteConfig,
) -> test_suite.BasicTestSuite:
    """create a test suite based on the config dict

    :param test_suite_dict: dict created from config with keys 'suite_dir',
        'test_filter_pattern', 'test_suite_id'
    """
    return test_suite.BasicTestSuite(
        test_suite_dict["suite_dir"],
        test_suite_dict["test_filter_pattern"],
        test_suite_dict["test_suite_id"],
    )


def apply_tag_filter(all_tests_to_run: unittest.TestSuite, usr_tags: Dict[str, List[str]]) -> None:
    """Filter the test cases based on user tags provided via CLI.

    :param all_tests_to_run: a dict containing all testsuites and testcases
    :param usr_tags: encapsulate user's variant choices
    """

    def format_tag_names(tags: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Remove any comma or underscore from the provided dict's keys."""
        for char in ["_", "-"]:
            tags = {name.replace(char, ""): value for name, value in tags.items()}
        return tags

    def should_skip(test_case: BasicTest) -> bool:
        """Check if test shall be skipped by evaluating the test case tag
        attribute.

        :param test_case: test_case to check
        :return: True if test shall be skipped else False
        """
        if test_case.tag is None:
            return False

        # Skip only the test cases that have a matching tag name but no matching tag value
        for cli_tag_id, cli_tag_value in usr_tags.items():
            # skip any test case that doesn't define a CLI-provided tag name
            if cli_tag_id not in test_case.tag.keys():
                test_case._skip_msg = f"provided tag {cli_tag_id!r} not present in test tags"
                return True
            # skip any test case that which tag value don't match the provided tag's value
            cli_tag_values = cli_tag_value if isinstance(cli_tag_value, list) else [cli_tag_value]
            if not any(cli_val in test_case.tag[cli_tag_id] for cli_val in cli_tag_values):
                test_case._skip_msg = f"non-matching value for tag {cli_tag_id!r}"
                return True

        return False

    def set_skipped(test_case: BasicTest) -> BasicTest:
        """Set testcase to skipped.

        :param test_case: testcase to be skipped
        :return: the skipped testcase as a new instance of the provided
            TestCase subclass.
        """
        if should_skip(test_case):
            skipped_test_cls = unittest.skip(test_case._skip_msg)(test_case.__class__)
            return skipped_test_cls()
        return test_case

    # collect and reformat all CLI and test case tag names
    usr_tags = format_tag_names(usr_tags)

    all_test_tags = []
    for tc in test_suite.flatten(all_tests_to_run):
        if getattr(tc, "tag", None) is None:
            continue
        tc.tag = format_tag_names(tc.tag)
        all_test_tags.extend(tc.tag.keys())

    # skip the tests according to the provided CLI tags and the defined test tags
    list(map(set_skipped, test_suite.flatten(all_tests_to_run)))

    # verify that each provided tag name is defined in at least one test case
    all_test_tags = set(all_test_tags)
    for tag_name in usr_tags:
        if tag_name not in all_test_tags:
            raise NameError(
                f"Provided tag {tag_name!r} is not defined in any testcase.",
                tag_name,
            )


def apply_test_case_filter(
    all_tests_to_run: unittest.TestSuite,
    test_class_pattern: str,
    test_case_pattern: str,
) -> unittest.TestSuite:
    """Apply a filter to run only test cases which matches given expression

    :param all_tests_to_run: a dict containing all testsuites and testcases
    :param test_class_pattern: pattern to select test class as unix filename pattern
    :param test_case_pattern: pattern to select test case as unix filename pattern
    :return: new test suite with filtered test cases
    """

    def is_active_test(test_case: BasicTest) -> bool:
        """Check if testcase shall be active by given selection patterns

        :param test_case: unittest test
        :return: True if test matches patterns else False
        """
        test_class_name = re.sub(r"-\d+-\d+", "", test_case.__class__.__name__)
        is_classname_match = bool(fnmatch(test_class_name, test_class_pattern))

        if is_classname_match and test_case_pattern is None:
            return is_classname_match
        elif is_classname_match and test_case_pattern:
            return bool(fnmatch(test_case._testMethodName, test_case_pattern))
        else:
            return False

    base_suite = test_suite.flatten(all_tests_to_run)
    filtered_suite = filter(is_active_test, base_suite)
    return unittest.TestSuite(filtered_suite)


def failure_and_error_handling(result: unittest.TestResult) -> int:
    """provide necessary information to Jenkins if an error occur during tests execution

    :param result: encapsulate all test results from the current run

    :return: an ExitCode object
    """
    failed, errored = result.failures, result.errors
    if failed and errored:
        exit_code = ExitCode.ONE_OR_MORE_TESTS_FAILED_AND_RAISED_UNEXPECTED_EXCEPTION
    elif failed:
        exit_code = ExitCode.ONE_OR_MORE_TESTS_FAILED
    elif errored:
        exit_code = ExitCode.ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION
    else:
        exit_code = ExitCode.ALL_TESTS_SUCCEEDED
    return exit_code


def enable_step_report(all_tests_to_run: unittest.suite.TestSuite, step_report: Path) -> None:
    """Decorate all assert method from Test-Case.

    This will allow to save the assert inputs in
    order to generate the HTML step report.

    :param all_tests_to_run: a dict containing all testsuites and testcases
    """

    # Step report header fed during test
    base_suite = test_suite.flatten(all_tests_to_run)
    for tc in base_suite:
        tc.step_report = StepReportData()
        if step_report is not None:
            # for any test, show ITF version
            tc.step_report.header = OrderedDict({"ITF version": pykiso.__version__})
            # Decorate All assert method
            assert_method_list = [method for method in dir(tc) if method.startswith("assert")]
            for method_name in assert_method_list:
                # Get method from name
                method = getattr(tc, method_name)
                # Add decorator to the existing method
                setattr(tc, method_name, assert_decorator(method))


def parse_test_selection_pattern(pattern: str) -> TestFilterPattern:
    """Parse test selection pattern from cli.

    For example: ``test_file.py::TestCaseClass::test_method``

    :param pattern: test selection pattern
    :return: pattern for file, class name and test case name
    """
    if not pattern:
        return TestFilterPattern(None, None, None)
    parsed_patterns = []
    patterns = pattern.split("::")
    for pattern in patterns:
        if pattern == "":
            parsed_patterns.append(None)
        else:
            parsed_patterns.append(pattern)
    for _ in range(3 - (len(parsed_patterns))):
        parsed_patterns.append(None)

    return TestFilterPattern(*parsed_patterns)


def find_folders_between_paths(start_path: Path, end_path: Path) -> List[Path]:
    """Find and return a list of folders between two specified paths.

    :param start_path: the starting path
    :param end_path: the ending path
    :return: a list of folders between `start_path` (exclusive) and `end_path` (inclusive). If `end_path` is not
        a subpath of `start_path`, an empty list is returned.
    """
    start_path = start_path
    end_path = end_path
    folders_between = []

    while start_path != end_path:
        folders_between.append(end_path.parent)
        end_path = end_path.parent
        if len(end_path.parents) == 1:
            return []
    return folders_between


def _is_valid_module(start_dir: str, pattern: str) -> bool:
    """Check if the test files found in the specified directory and its subdirectories
    conform to the requirements of a valid module.

    :param start_dir: the directory to search
    :param pattern: pattern that matches the file names
    """
    start_dir = Path(start_dir)
    test_files_found = list(start_dir.glob(f"**/{pattern}"))

    # remove folders
    test_files_found = [test_file for test_file in test_files_found if test_file.is_file()]

    # If found test files are in given test suite directory don't check for __init__.py
    if any(test_file.parent == start_dir for test_file in test_files_found):
        return True

    # No file matches the test filter pattern
    if not test_files_found:
        log.critical(f"Test filter {pattern=} doesn't match any files in folder {start_dir}")
        return False

    # Check that all sub folders of a nested testsuite have an __init__.py file
    testsuite_folders = {filepath.parent for filepath in test_files_found}
    all_folders_to_check = []
    for folder in testsuite_folders:
        all_folders_to_check.extend(find_folders_between_paths(start_dir, folder))
    all_folders_to_check.extend(testsuite_folders)
    all_folders_to_check = list(set(all_folders_to_check))

    if start_dir in all_folders_to_check:
        all_folders_to_check.remove(start_dir)

    for folder in all_folders_to_check:
        if not any(file_path.name == "__init__.py" for file_path in folder.iterdir()):
            log.critical(f'Could not find file "__init__.py" in folder {folder}')
            return False

    # check that the test file has a valid module name
    return all(VALID_MODULE_NAME.match(file.name) for file in test_files_found)


def filter_test_modules_by_suite(
    test_modules: List[SuiteConfig],
) -> List[SuiteConfig]:
    """Filter a list of test modules by their suite directory to avoid running duplicates.

    :param test_modules: List of test modules to filter.
    :return: Filtered list of test modules with unique suite directories
    """
    seen_suite_dirs = {}
    filtered_data = []

    for module in test_modules:
        suite_dir = module["suite_dir"]

        # Check if the suite directory is seen for the first time
        if suite_dir not in seen_suite_dirs:
            seen_suite_dirs[suite_dir] = module
            filtered_data.append(module)

    return filtered_data


def collect_test_suites(
    config_test_suite_list: List[SuiteConfig],
    test_filter_pattern: Optional[str] = None,
) -> List[test_suite.BasicTestSuite]:
    """Collect and load all test suites defined in the test configuration.

    :param config_test_suite_list: list of dictionaries from the configuration
        file corresponding each to one test suite.
    :param test_filter_pattern: optional filter pattern to overwrite
        the one defined in the test suite configuration.

    :raises pykiso.TestCollectionError: if any test case inside one of
        the configured test suites failed to be loaded.

    :return: a list of all loaded test suites.
    """
    list_of_test_suites = []
    valid_test_modules = []

    for test_suite_configuration in config_test_suite_list:
        if test_filter_pattern is not None:
            test_suite_configuration["test_filter_pattern"] = test_filter_pattern

        if _is_valid_module(
            start_dir=test_suite_configuration["suite_dir"],
            pattern=test_suite_configuration["test_filter_pattern"],
        ):
            valid_test_modules.append(test_suite_configuration)

    if test_filter_pattern:
        valid_test_modules = filter_test_modules_by_suite(valid_test_modules)

    if not valid_test_modules:
        raise TestCollectionError([test_suite_config["suite_dir"] for test_suite_config in config_test_suite_list])

    for test_suite_configuration in valid_test_modules:
        try:
            current_test_suite = create_test_suite(test_suite_configuration)
            list_of_test_suites.append(current_test_suite)
        except BaseException as e:
            raise TestCollectionError(test_suite_configuration["suite_dir"]) from e
    return list_of_test_suites


def abort(reason: str = None) -> None:
    """Quit ITF test and log an error if a reason is indicated and
    if any errors occurred it logs them.

    :param reason: reason to abort, defaults to None
    """
    if reason:
        log.critical(reason)
    log.critical("Non recoverable error occurred during test execution, aborting test session.")
    os.kill(os.getpid(), ExitCode.ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION)


def execute(
    config: ConfigDict,
    report_type: str = "text",
    report_name: str = "",
    user_tags: Optional[Dict[str, List[str]]] = None,
    step_report: Optional[Path] = None,
    pattern_inject: Optional[str] = None,
    failfast: bool = False,
    junit_path: str = "reports",
) -> int:
    """Create test environment based on test configuration.

    :param config: dict from converted YAML config file
    :param report_type: str to set the type of report wanted, i.e. test
        or junit
    :param report_name: name of the junit report
    :param user_tags: test case tags to execute
    :param step_report: file path for the step report or None
    :param pattern_inject: optional pattern that will override
        test_filter_pattern for all suites. Used in test development to
        run specific tests.
    :param failfast: stop the test run on the first error or failure.
    :param junit_path: path (file or dir) to junit report

    :return: exit code corresponding to the result of the test execution
        (tests failed, unexpected exception, ...)
    """
    try:
        test_file_pattern = parse_test_selection_pattern(pattern_inject)

        test_suites = collect_test_suites(config["test_suite_list"], test_file_pattern.test_file)
        test_suites = handle_can_trace_strategy(config, test_suites)
        # Group all the collected test suites in one global test suite
        all_tests_to_run = unittest.TestSuite(test_suites)

        # filter test cases based on variant and branch-level options
        if user_tags:
            apply_tag_filter(all_tests_to_run, user_tags)

        # Enable step report
        enable_step_report(all_tests_to_run, step_report)

        if test_file_pattern.test_class:
            all_tests_to_run = apply_test_case_filter(
                all_tests_to_run,
                test_file_pattern.test_class,
                test_file_pattern.test_case,
            )

        log_file_path = get_logging_options().log_path
        # TestRunner selection: generate or not a junit report. Start the tests and publish the results
        if report_type == "junit":
            report_path = junit_path
            full_report_path = Path.cwd() / report_path
            if full_report_path.suffix == ".xml":
                junit_report_path = str(full_report_path)
                full_report_path.parent.mkdir(exist_ok=True)
            else:
                junit_report_path = str(full_report_path / Path(time.strftime(f"%Y-%m-%d_%H-%M-%S-{report_name}.xml")))
                full_report_path.mkdir(exist_ok=True)
            with open(junit_report_path, "wb") as junit_output, ResultStream(log_file_path) as stream:
                test_runner = xmlrunner.XMLTestRunner(
                    output=junit_output,
                    resultclass=MultiTestResult(XmlTestResult, BannerTestResult),
                    failfast=failfast,
                    verbosity=0,
                    stream=stream,
                )
                result = test_runner.run(all_tests_to_run)
        else:
            with ResultStream(log_file_path) as stream:
                test_runner = unittest.TextTestRunner(
                    stream=stream,
                    resultclass=MultiTestResult(BannerTestResult),
                    failfast=failfast,
                    verbosity=0,
                )
                result = test_runner.run(all_tests_to_run)

        # Generate the html step report
        if step_report is not None:
            generate_step_report(result, step_report)

        exit_code = failure_and_error_handling(result)
    except NameError:
        log.exception("Error occurred during tag evaluation.")
        exit_code = ExitCode.BAD_CLI_USAGE
    except TestCollectionError:
        log.exception("Error occurred during test collection.")
        exit_code = ExitCode.ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION
    except AuxiliaryCreationError:
        log.exception("Error occurred during auxiliary creation.")
        exit_code = ExitCode.AUXILIARY_CREATION_FAILED
    except KeyboardInterrupt:
        log.exception("Keyboard Interrupt detected")
        exit_code = ExitCode.ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION
    except Exception:
        log.exception(f'Issue detected in the test-suite: {config["test_suite_list"]}!')
        exit_code = ExitCode.ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION
    return int(exit_code)


def handle_can_trace_strategy(
    config: dict[str, Any], test_suites: list[unittest.TestSuite]
) -> list[unittest.TestSuite]:
    """Setup the test to get a trace file for every test or testCase if the user requested it
        else just return the test suite passed in input

    :param config: dict from converted YAML config file
    :return: a list of all loaded test suites.

    :return: a list of all loaded test suites with setUp and tearDown modified if needed.
    """
    if not _check_trace_file_strategy(config):
        return test_suites
    can_channel = _get_connector_instance_with_trace_file_strategy(config)
    if can_channel is None:
        return test_suites

    # Decorate function to call the start and stop pcan trace function
    list_class: list[type[unittest.TestCase]] = []
    for suite in test_suites:
        for test in suite._tests:
            # If the user want to have one trace file for a testCase we decorate the setUpClass and tearDownClass
            if can_channel.strategy_trc_file == "testCase":
                trc_file_name = util.strclass(test.__class__).replace(".", "_").replace("-", "_") + ".trc"
                test_class = test.__class__
                if test_class in list_class:
                    continue
                list_class.append(test_class)
                test_class.setUpClass = start_can_trace_decorator(test_class.setUpClass, can_channel, trc_file_name)
                test_class.tearDownClass = stop_can_trace_decorator(test_class.tearDownClass, can_channel)

            # If the user want to have one trace file for each test run we decorate the setUp and tearDown of the class
            elif can_channel.strategy_trc_file == "testRun":
                trc_file_name = (
                    util.strclass(test.__class__).replace(".", "_").replace("-", "_")
                    + "_"
                    + test._testMethodName
                    + ".trc"
                )
                test.setUp = start_can_trace_decorator(test.setUp, can_channel, trc_file_name)
                test.tearDown = stop_can_trace_decorator(test.tearDown, can_channel)
    return test_suites


def _get_connector_instance_with_trace_file_strategy(config: dict[str, Any]) -> Optional[Union[CCPCanCan, CCSocketCan]]:
    """Get pcan and socket can channels from auxiliaries created from the Yaml

    :param config: dict from converted YAML config file
    :return: the channel instance if one was created else False
    """
    from ..lib.connectors.cc_pcan_can import CCPCanCan
    from ..lib.connectors.cc_proxy import CCProxy
    from ..lib.connectors.cc_socket_can import CCSocketCan

    # Retrieve the channel from the auxiliaries defined
    for aux in config["auxiliaries"].keys():
        instance_channel = getattr(getattr(pykiso.auxiliaries, aux, None), "channel", None)
        if isinstance(instance_channel, CCProxy):
            instance_channel = instance_channel._proxy.channel
        if isinstance(instance_channel, (CCPCanCan, CCSocketCan)) and instance_channel.strategy_trc_file in [
            "testRun",
            "testCase",
        ]:
            return instance_channel
    return None


def _check_trace_file_strategy(config: dict[str, Any]) -> bool:
    """Check if at least one connector has the trace file strategy flag active

    :param config: dict from converted YAML config file

    :return: True if a connector has a trace file strategy active else False
    """
    strategy_trc_file = None
    # Check if a pcan with the right parameter is defined in the config
    for connector in config["connectors"].values():
        connector_config = connector.get("config", {})
        if connector_config is not None and "strategy_trc_file" in connector.get("config", {}).keys():
            strategy_trc_file = connector["config"]["strategy_trc_file"]
            if strategy_trc_file not in ["testRun", "testCase"]:
                raise ValueError(
                    f"{strategy_trc_file} is not a valid value for strategy_trc_file, ",
                    "valid values are ['testRun','testCase']",
                )
    return strategy_trc_file is not None


def start_can_trace_decorator(func: Callable, channel: Union[CCPCanCan, CCSocketCan], trace_file_name: str):
    """Decorator that will call start pcan trace before calling the function

    :param func: function to execute
    :param cc_pcan: channel used to get the pcan trace
    :param trace_file_name: name of the trace file to create
    """

    @functools.wraps(func)
    def decorator(*args, **kwargs):
        from ..lib.connectors.cc_pcan_can import CCPCanCan

        # Add datetime in trace file name to not overwrite trace file when rerunning test
        if not channel.opened:
            channel.open()
        trace_path = channel.trace_path / trace_file_name.replace(
            ".trc", f"_{datetime.today().strftime('%Y%d%m%H%M%S')}.trc"
        )
        if isinstance(channel, CCPCanCan):
            channel.start_pcan_trace(trace_path=trace_path)
        else:
            channel.start_can_trace(trace_path=trace_path)
        return func(*args, **kwargs)

    return decorator


def stop_can_trace_decorator(func: Callable, channel: Union[CCPCanCan, CCSocketCan]):
    """Decorator that will call stop pcan trace after calling the function

    :param func: function to execute
    :param channel: channel used to get the pcan trace
    """

    @functools.wraps(func)
    def decorator(*args, **kwargs):
        from ..lib.connectors.cc_pcan_can import CCPCanCan

        result = func(*args, **kwargs)
        if isinstance(channel, CCPCanCan):
            channel.stop_pcan_trace()
        else:
            channel.stop_can_trace()
        return result

    return decorator
