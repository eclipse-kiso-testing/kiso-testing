##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Test Suite
**********

:module: test_suite

:synopsis: Create a generic test-suite based on the connected modules, and
    gray test-suite for Message Protocol / TestApp usage.

.. currentmodule:: generic_test_suite


"""
from __future__ import annotations

import logging
import unittest
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Dict, List, Union
from unittest.suite import _isnotsuite

from .. import message
from ..auxiliary import AuxiliaryInterface
from .test_message_handler import test_app_interaction

if TYPE_CHECKING:
    from ..test_result.text_result import BannerTestResult
    from .test_case import BasicTest

__all__ = [
    "BaseTestSuite",
    "BasicTestSuiteSetup",
    "BasicTestSuiteTeardown",
    "RemoteTestSuiteSetup",
    "RemoteTestSuiteTeardown",
    "BasicTestSuite",
]

log = logging.getLogger(__name__)


class BaseTestSuite(unittest.TestCase):
    response_timeout = 10

    def __init__(
        self,
        test_suite_id: int,
        test_case_id: int,
        aux_list: Union[List[AuxiliaryInterface], None],
        setup_timeout: Union[int, None],
        run_timeout: Union[int, None],
        teardown_timeout: Union[int, None],
        test_ids: Union[dict, None],
        tag: Union[Dict[str, List[str]], None],
        *args: Any,
        **kwargs: Any,
    ):
        """Initialize generic test-case.

        :param test_suite_id: test suite identification number
        :param test_case_id: test case identification number
        :param aux_list: list of used auxiliaries
        :param setup_timeout: maximum time (in seconds) used to wait
            for a report during setup execution
        :param run_timeout: maximum time (in seconds) used to wait for
            a report during test_run execution
        :param teardown_timeout: the maximum time (in seconds) used to
            wait for a report during teardown execution
        :param test_ids: jama references to get the coverage
            eg: {"Component1": ["Req1", "Req2"], "Component2": ["Req3"]}
        :param tag: dictionary containing lists of variants and/or test levels
            when only a subset of tests needs to be executed
        """
        # Initialize base class
        super().__init__(*args, **kwargs)
        # Save test information
        self.test_auxiliary_list = aux_list or []
        self.test_suite_id = test_suite_id
        self.test_case_id = test_case_id
        self.test_ids = test_ids
        self.tag = tag
        self.start_time = self.stop_time = self.elapsed_time = 0

    def cleanup_and_skip(self, aux: AuxiliaryInterface, info_to_print: str):
        """Cleanup auxiliary and log reasons.

        :param aux: corresponding auxiliary to abort
        :param info_to_print: A message you want to print while cleaning up the test
        """
        # Log error message
        log.critical(info_to_print)

        # Send aborts to corresponding auxiliary
        if aux.send_abort_command(timeout=10) is not True:
            log.critical(f"Error occurred during abort command on auxiliary {aux}")

        self.fail(info_to_print)

    def __str__(self):
        return "%s (%s)" % (self._testMethodName, self.__class__.__name__)


class BasicTestSuiteSetup(BaseTestSuite):
    """Inherit from unittest testCase and represent setup fixture."""

    def __init__(
        self,
        test_suite_id: int,
        test_case_id: int,
        aux_list: Union[List[AuxiliaryInterface], None],
        setup_timeout: Union[int, None],
        run_timeout: Union[int, None],
        teardown_timeout: Union[int, None],
        test_ids: Union[dict, None],
        tag: Union[Dict[str, List[str]], None],
        *args: Any,
        **kwargs: Any,
    ):
        """Initialize Message Protocol / TestApp test-case.

        :param test_suite_id: test suite identification number
        :param test_case_id: test case identification number
        :param aux_list: list of used auxiliaries
        :param setup_timeout: maximum time (in seconds) used to wait
            for a report during setup execution
        :param run_timeout: maximum time (in seconds) used to wait for
            a report during test_run execution
        :param teardown_timeout: the maximum time (in seconds) used to
            wait for a report during teardown execution
        :param test_ids: jama references to get the coverage
            eg: {"Component1": ["Req1", "Req2"], "Component2": ["Req3"]}
        :param tag: dictionary containing lists of variants and/or test levels
            when only a subset of tests needs to be executed
        """
        super().__init__(
            test_suite_id,
            test_case_id,
            aux_list,
            setup_timeout,
            run_timeout,
            teardown_timeout,
            test_ids,
            tag,
            *args,
            **kwargs,
        )
        if any([setup_timeout, run_timeout, teardown_timeout]):
            log.warning("BasicTestSuiteSetup does not support test timeouts, it will be discarded")

    def test_suite_setUp(self):
        """Test method for constructing the actual test suite."""
        pass


class BasicTestSuiteTeardown(BaseTestSuite):
    """Inherit from unittest testCase and represent teardown fixture."""

    def __init__(
        self,
        test_suite_id: int,
        test_case_id: int,
        aux_list: Union[List[AuxiliaryInterface], None],
        setup_timeout: Union[int, None],
        run_timeout: Union[int, None],
        teardown_timeout: Union[int, None],
        test_ids: Union[dict, None],
        tag: Union[Dict[str, List[str]], None],
        *args: Any,
        **kwargs: Any,
    ):
        """Initialize Message Protocol / TestApp test-case.

        :param test_suite_id: test suite identification number
        :param test_case_id: test case identification number
        :param aux_list: list of used auxiliaries
        :param setup_timeout: maximum time (in seconds) used to wait
            for a report during setup execution
        :param run_timeout: maximum time (in seconds) used to wait for
            a report during test_run execution
        :param teardown_timeout: the maximum time (in seconds) used to
            wait for a report during teardown execution
        :param test_ids: jama references to get the coverage
            eg: {"Component1": ["Req1", "Req2"], "Component2": ["Req3"]}
        :param tag: dictionary containing lists of variants and/or test levels
            when only a subset of tests needs to be executed
        """
        super().__init__(
            test_suite_id,
            test_case_id,
            aux_list,
            setup_timeout,
            run_timeout,
            teardown_timeout,
            test_ids,
            tag,
            *args,
            **kwargs,
        )
        if any([setup_timeout, run_timeout, teardown_timeout]):
            log.warning("BasicTestSuiteTeardown does not support test timeouts, it will be discarded")

    def test_suite_tearDown(self):
        """Test method for deconstructing the actual test suite after testing it."""
        pass


class RemoteTestSuiteSetup(BasicTestSuiteSetup):
    """Inherit from unittest testCase and represent setup fixture
    when Message Protocol / TestApp  is used.
    """

    response_timeout = 10

    def __init__(
        self,
        test_suite_id: int,
        test_case_id: int,
        aux_list: Union[List[AuxiliaryInterface], None],
        setup_timeout: Union[int, None],
        run_timeout: Union[int, None],
        teardown_timeout: Union[int, None],
        test_ids: Union[dict, None],
        tag: Union[Dict[str, List[str]], None],
        *args: Any,
        **kwargs: Any,
    ):
        """Initialize Message Protocol / TestApp test-case.

        :param test_suite_id: test suite identification number
        :param test_case_id: test case identification number
        :param aux_list: list of used auxiliaries
        :param setup_timeout: maximum time (in seconds) used to wait
            for a report during setup execution
        :param run_timeout: maximum time (in seconds) used to wait for
            a report during test_run execution
        :param teardown_timeout: the maximum time (in seconds) used to
            wait for a report during teardown execution
        :param test_ids: jama references to get the coverage
            eg: {"Component1": ["Req1", "Req2"], "Component2": ["Req3"]}
        :param tag: dictionary containing lists of variants and/or test levels
            when only a subset of tests needs to be executed
        """
        super().__init__(
            test_suite_id,
            test_case_id,
            aux_list,
            setup_timeout,
            run_timeout,
            teardown_timeout,
            test_ids,
            tag,
            *args,
            **kwargs,
        )
        self.setup_timeout = setup_timeout or RemoteTestSuiteSetup.response_timeout
        self.run_timeout = run_timeout or RemoteTestSuiteSetup.response_timeout
        self.teardown_timeout = teardown_timeout or RemoteTestSuiteSetup.response_timeout

    @test_app_interaction(message_type=message.MessageCommandType.TEST_SUITE_SETUP, timeout_cmd=5)
    def test_suite_setUp(self):
        """Test method for constructing the actual test suite."""
        pass


class RemoteTestSuiteTeardown(BasicTestSuiteTeardown):
    """Inherit from unittest testCase and represent teardown fixture
    when Message Protocol / TestApp is used.
    """

    response_timeout = 10

    def __init__(
        self,
        test_suite_id: int,
        test_case_id: int,
        aux_list: Union[List[AuxiliaryInterface], None],
        setup_timeout: Union[int, None],
        run_timeout: Union[int, None],
        teardown_timeout: Union[int, None],
        test_ids: Union[dict, None],
        tag: Union[Dict[str, List[str]], None],
        *args: Any,
        **kwargs: Any,
    ):
        """Initialize Message Protocol / TestApp test-case.

        :param test_suite_id: test suite identification number
        :param test_case_id: test case identification number
        :param aux_list: list of used auxiliaries
        :param setup_timeout: maximum time (in seconds) used to wait
            for a report during setup execution
        :param run_timeout: maximum time (in seconds) used to wait for
            a report during test_run execution
        :param teardown_timeout: the maximum time (in seconds) used to
            wait for a report during teardown execution
        :param test_ids: jama references to get the coverage
            eg: {"Component1": ["Req1", "Req2"], "Component2": ["Req3"]}
        :param tag: dictionary containing lists of variants and/or test levels
            when only a subset of tests needs to be executed
        """
        super().__init__(
            test_suite_id,
            test_case_id,
            aux_list,
            setup_timeout,
            run_timeout,
            teardown_timeout,
            test_ids,
            tag,
            *args,
            **kwargs,
        )
        self.setup_timeout = setup_timeout or RemoteTestSuiteTeardown.response_timeout
        self.run_timeout = run_timeout or RemoteTestSuiteTeardown.response_timeout
        self.teardown_timeout = teardown_timeout or RemoteTestSuiteTeardown.response_timeout

    @test_app_interaction(
        message_type=message.MessageCommandType.TEST_SUITE_TEARDOWN,
        timeout_cmd=5,
    )
    def test_suite_tearDown(self):
        """Test method for deconstructing the actual test suite after testing it."""
        pass


class BasicTestSuite(unittest.TestSuite):
    """Inherit from the unittest framework test-suite but build it for our integration tests."""

    def __init__(
        self,
        modules_to_add_dir: str,
        test_filter_pattern: str,
        test_suite_id: int,
        *args: Any,
        **kwargs: Any,
    ):
        """Initialize our custom unittest-test-suite.

        .. note::
            1. Will Load from the given path the integration test modules under test
            2. Sort the given test case list by test suite/case id
            3. Place Test suite setup and teardown respectively at top and bottom of test case list
            4. Add sorted test case list to test suite
        """
        # Mother class initialization
        super().__init__(*args, **kwargs)

        # load test from the specified folder
        loader = unittest.TestLoader()
        found_modules = loader.discover(modules_to_add_dir, pattern=test_filter_pattern)

        # sort the test case list by ascendant using test suite and test case id
        test_case_list = sorted(flatten(found_modules), key=tc_sort_key)

        # add sorted test case list to test suite
        self.addTests(test_case_list)

        self.failed_suite_setups = set()

    def check_suite_setup_failed(self, test: BasicTest, result: BannerTestResult) -> None:
        """Check if the suite setup has failed and store failed suite id.
        Search in the global unittest result object, which save all the results
        of the tests performed up to that point, if the suite setup that ran
        has failed then store the suite id.

        :param test: test to check
        :param result: unittest result object
        """
        if isinstance(test, BasicTestSuiteSetup):
            if result.error_occurred:
                self.failed_suite_setups.add(test.test_suite_id)

    def run(self, result: BannerTestResult, debug: bool = False) -> BannerTestResult:
        """Override run method from unittest.suite.TestSuite.
        Added functionality:
        Skip suite tests if the parent test suite setup has failed.

        :param result: unittest result storage
        :param debug: True to enter debug mode, defaults to False
        :return: test suite result
        """
        topLevel = False
        if getattr(result, "_testRunEntered", False) is False:
            result._testRunEntered = topLevel = True

        for index, test in enumerate(self):
            if result.shouldStop:  # pragma: no cover
                break

            if _isnotsuite(test):
                self._tearDownPreviousClass(test, result)
                self._handleModuleFixture(test, result)
                self._handleClassSetUp(test, result)
                result._previousTestClass = test.__class__

                if getattr(test.__class__, "_classSetupFailed", False) or getattr(
                    result, "_moduleSetUpFailed", False
                ):  # pragma: no cover
                    continue

            if not debug:
                if test.test_suite_id in self.failed_suite_setups:
                    result.addSkip(
                        test,
                        f"Suite Setup failed for test suite {test.test_suite_id}",
                    )
                else:
                    test(result)
                    self.check_suite_setup_failed(test, result)

            else:  # pragma: no cover
                test.debug()

            if self._cleanup:
                self._removeTestAtIndex(index)

        if topLevel:
            self._tearDownPreviousClass(None, result)
            self._handleModuleTearDown(result)
            result._testRunEntered = False
        return result


def tc_sort_key(tc):
    """Sort-key for testcases.

    will sort by test-suite/test-case, but the setup will always be first,
    the teardown will always be last.

    :param tc: a Base or Remote TestSuite/TestCase to rank

    :return: key for :py:func:`sorted`

    :raises: any exception that occurs during test loading
    """
    fix_ind = 0
    if isinstance(tc, (BasicTestSuiteSetup, RemoteTestSuiteSetup)):
        fix_ind = -1
    elif isinstance(tc, (BasicTestSuiteTeardown, RemoteTestSuiteTeardown)):
        fix_ind = 1
    elif isinstance(tc, unittest.loader._FailedTest):
        raise tc._exception
    return (fix_ind, tc.test_suite_id, tc.test_case_id)


def flatten(it: unittest.TestSuite) -> Iterable[BasicTest]:
    """Flatten all level of nesting.

    :param it: nested iterable
    :return: first not nested items
    """
    for x in it:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            yield from flatten(x)
        else:
            yield x
