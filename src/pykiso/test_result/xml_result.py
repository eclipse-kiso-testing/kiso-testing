##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
XML test result for JUnit support
*********************************

:module: xml_result

:synopsis: overwrite xmlrunner.result to add the test IDs
    into the xml report.

.. currentmodule:: xml_result
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from io import TextIOWrapper
from types import TracebackType
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Type

if TYPE_CHECKING:
    from unittest.case import TestCase
    from xml.dom.minidom import Document, Element
    from ..test_coordinator.test_case import BasicTest

import xmlrunner.result
import xmlrunner.runner

from pykiso.logging_initializer import get_logging_options, initialize_logging


class TestInfo(xmlrunner.result._TestInfo):
    """This class keeps useful information about the execution of a test method.
    Used by XmlTestResult
    """

    __test__ = False

    def __init__(
        self,
        test_result: xmlrunner.runner._XMLTestResult,
        test_case: BasicTest,
        outcome: int = 0,
        err: Optional[Tuple[Type[BaseException], BaseException, TracebackType]] = None,
        subTest: TestCase = None,
        filename: Optional[str] = None,
        lineno: Optional[bool] = None,
        doc: Optional[str] = None,
    ):
        """Initialize the TestInfo class and append additional tag
           that have to be stored for each test

        :param test_result: test result class
        :param test_method: test method (dynamically created eg: test_case.MyTest2-1-2)
        :param outcome: result of the test (SUCCESS, FAILURE, ERROR, SKIP)
        :param err: exception information of an error that was raised during the test
        :param subTest: optional subTest that was run
        :param filename: name of the file
        :param lineno: store the test line number
        :param doc: additional documentation to store
        """
        super().__init__(
            test_result,
            test_case,
            outcome,
            err,
            subTest,
            filename,
            lineno,
            doc,
        )

        # reinitialize logging inside XmlTestRunner's run
        # otherwise stdout is never caught in the JUnit report
        log_options = get_logging_options()
        initialize_logging(
            log_options.log_path,
            log_options.log_level,
            log_options.verbose,
            log_options.report_type,
        )

        # handle class setup error
        if isinstance(test_case, unittest.suite._ErrorHolder):
            test_case._testMethodDoc = ""
            test_case.test_ids = {}

        self._test = test_case
        # add attribute that will be used to format the errors
        self._testMethodDoc = test_case._testMethodDoc
        # store extra tag
        self.test_ids = json.dumps(test_case.test_ids)

    def __repr__(self) -> str:
        """Return the same representation as the one of unittest.TestCase.

        :return: the wrapped test case's representation.
        """
        *modules, test_case, test_method = self.test_id.split(".")
        return f"{test_method} ({'.'.join(modules)}.{test_case})"


class XmlTestResult(xmlrunner.runner._XMLTestResult):
    """
    Test result class that can express test results in a XML report.
    Used by XMLTestRunner.
    """

    def __init__(
        self,
        stream: TextIOWrapper = sys.stderr,
        descriptions: bool = True,
        verbosity: int = 0,
        elapsed_times: bool = True,
        properties: Optional[Dict[str, Any]] = None,
        infoclass: Type[TestInfo] = TestInfo,
    ):
        """Initialize both base classes with the appropriate parameters.

        :param stream: buffered text interface to a buffered raw stream
        :param descriptions: include description of the test
        :param verbosity: print output into the console
        :param elapsed_times: include the time spend on the test
        :param properties: junit testsuite properties
        :param infoclass: class containing the test information
        """
        xmlrunner.runner._XMLTestResult.__init__(
            self,
            stream=stream,
            descriptions=descriptions,
            verbosity=verbosity,
            elapsed_times=elapsed_times,
            properties=properties,
            infoclass=infoclass,
        )

    def addSuccess(self, test: TestCase) -> None:
        """Calls only _XMLTestResult's addSuccess as BannerTestResult's
        appends TestCase instances to the successes list, but _XMLTestResult
        wraps them in TestInfo instances with additional attributes.

        :param test: current succeeded TestCase.
        """
        return xmlrunner.runner._XMLTestResult.addSuccess(self, test)

    # save the original staticmethod that will be overwritten in order to call it
    report_testcase = copy.deepcopy(xmlrunner.runner._XMLTestResult._report_testcase)

    @staticmethod
    def _report_testcase(test_result: TestInfo, xml_testsuite: Element, xml_document: Document):
        """Callback function that create the test case section into the XML document.

        :param test_result: result of a test run
        :param xml_testsuite: xml test suite to be written
        :param xml_document: xml document base
        """
        # call the original method
        XmlTestResult.report_testcase(test_result, xml_testsuite, xml_document)

        # add user-defined properties to the test cases if any
        xml_testcases = xml_testsuite.getElementsByTagName("testcase")
        for xml_testcase in xml_testcases:
            testcase_properties = getattr(test_result._test, "properties", None)
            if not isinstance(testcase_properties, dict):
                break
            # avoid adding the same properties to the same testcase multiple times
            if xml_testcase.getElementsByTagName("properties"):
                continue
            # add the properties to the testcase
            XmlTestResult._report_testsuite_properties(xml_testcase, xml_document, testcase_properties)

        # here can be added additional tags that have to be stored into the xml test report
        xml_testsuite.setAttribute("test_ids", str(test_result.test_ids))

    # Overwrite the original staticmethod xmlrunner.runner._XMLTestResult._report_testcase with ours
    xmlrunner.runner._XMLTestResult._report_testcase = _report_testcase
