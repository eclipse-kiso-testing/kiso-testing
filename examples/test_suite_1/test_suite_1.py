##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
test_suite_1
************
:module: test_suite_1
:synopsis: Basic example on how to write and configure test suite and
case on ITF side in order to communicate with the device under test
using TestApp.
"""

import importlib
import logging
import time
from itertools import cycle

import pykiso
import pykiso.profiling
from pykiso.auxiliaries import aux1, aux2, aux3
from pykiso.profiling import get_tracer, profile_manager

# define an external iterator that can be used for retry_test_case demo
side_effect = cycle([False, False, True])


@pykiso.define_test_parameters(suite_id=1, aux_list=[aux1, aux2])
class SuiteSetup(pykiso.RemoteTestSuiteSetup):
    """This test suite setup will be executed using base behavior
    given by RemoteTestSuiteSetup.
    Using decorator define_test_parameters the following parameters will
    be applied on test suite setup :
    -> suite_id : set to 1
    -> aux_list : test suite setup executed using aux1 and aux2 (see
    yaml configuration file)
    """

    def test_suite_setUp(self):
        module = importlib.import_module("pykiso.auxiliaries")
        attribute = dir(module)
        logging.error(f"this is the attribute of pykiso.auxiliaries: {attribute}")


@pykiso.define_test_parameters(suite_id=1, aux_list=[aux1, aux2])
class SuiteTearDown(pykiso.RemoteTestSuiteTeardown):
    """This test suite teardown will be executed using base behavior
    given by RemoteTestSuiteSetup.
    Using decorator define_test_parameters the following parameters will
    be applied on test suite teardown :
    -> suite_id : set to 1
    -> aux_list : test suite teardown executed using aux1 and aux2 (see
    yaml configuration file)
    """


@pykiso.define_test_parameters(
    suite_id=1,
    case_id=1,
    aux_list=[aux1],
    test_ids={
        "Component1": ["Req1", "Req2"],
        "Component2": ["Req3"],
        "VTestId": ["1234456", "123456"],
    },
    tag={"variant": ["variant1"], "branch_level": ["daily"]},
)
class MyTest1(pykiso.BasicTest):
    """This test case definition will be executed using base behavior
    given by RemoteTest only for setUp and tearDown method.
    Using decorator define_test_parameters the following parameters will
    be applied on test case setUp and tearDown:
    -> suite_id : set to 1
    -> case_id : set to 1
    -> aux_list : test case test_run, setUp, and tearDown executed using
    aux1 (see yaml configuration file)
    -> test_ids: [optional] store the requirements into the report
    -> tag: [optional] allows the run of subset of tests
    """

    def setUp(self):
        """Hook method from unittest in order to execute code before test case run.
        In this case the default setUp method is overridden, allowing us to apply the
        retry_test_case's decorator. The syntax super() access to the BasicTest and
        we will run the default setUp()
        """
        super().setUp()

    @pykiso.profiling.profile(compress=False)
    def test_run1(self):
        """In this case the default test_run method is overridden and
        instead of calling test_run from RemoteTest class the following
        code is called.
        Here, the test pass at the 3rd attempt out of 5. The setup and
        tearDown methods are called for each attempt.
        """
        logging.info("TAG daily")
        logging.info(f"--------------- RUN: {self.test_suite_id}, {self.test_case_id} ---------------")
        # define any additional key-value pair that will appear as property in the JUnit report
        self.properties = {"testrail_attachment": "some/path/to/afile.txt"}
        time.sleep(1)
        logging.info(f"I HAVE RUN 0.1.1 for tag {self.tag}!")
        self.assertTrue(True)

    def test_run2(self):
        """In this case the default test_run method is overridden and
        instead of calling test_run from RemoteTest class the following
        code is called.
        Here, the test pass at the 3rd attempt out of 5. The setup and
        tearDown methods are called for each attempt.
        """
        logging.info("TAG daily")
        logging.info(f"--------------- RUN: {self.test_suite_id}, {self.test_case_id} ---------------")
        # define any additional key-value pair that will appear as property in the JUnit report
        with profile_manager("testrun2.json", compress=False):
            time.sleep(1)
            logging.info(f"I HAVE RUN 0.1.1 for tag {self.tag}!")
        time.sleep(1)
        self.assertTrue(True)
        logging.info(f"I HAVE RUN 0.1.1 for tag {self.tag}!")

    def test_run3(self):
        """In this case the default test_run method is overridden and
        instead of calling test_run from RemoteTest class the following
        code is called.
        Here, the test pass at the 3rd attempt out of 5. The setup and
        tearDown methods are called for each attempt.
        """
        logging.info("TAG daily")
        logging.info(f"--------------- RUN: {self.test_suite_id}, {self.test_case_id} ---------------")
        # define any additional key-value pair that will appear as property in the JUnit report
        time.sleep(1)
        local_tracer = get_tracer()
        local_tracer.start()
        logging.info(f"I HAVE RUN 0.1.1 for tag {self.tag}!")
        time.sleep(1)
        local_tracer.stop()
        local_tracer.save("testrun3.json")
        logging.info(f"I HAVE RUN 0.1.1 for tag {self.tag}!")
        self.assertTrue(True)

    @pykiso.retry_test_case(max_try=3)
    def tearDown(self):
        """Hook method from unittest in order to execute code after the test case ran.
        In this case the default tearDown method is overridden, allowing us to apply the
        retry_test_case's decorator. The syntax super() access to the BasicTest and
        we will run the default tearDown()
        """
        super().tearDown()
