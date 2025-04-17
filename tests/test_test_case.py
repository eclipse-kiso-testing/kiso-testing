##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

import logging
import unittest
from collections import OrderedDict
from functools import partial

import pytest

import pykiso.test_result.assert_step_report as step_report
from pykiso import cli, retry_test_case, xray
from pykiso.logging_initializer import LogOptions
from pykiso.test_coordinator import test_case


@pytest.mark.usefixtures("CustomTestCaseAndSuite")
class IntegrationTestCase(unittest.TestCase):
    def test_load_test_case(self):
        """run a default test case (see conftest.py), using existing auxiliaries
        (ExampleAuxiliary) and connectors (CCExample)

        Validation criteria:
        -  sub class from test_case.BasicTest behave like unittest.TestCase
        -  all test are PASSED
        -  no error are reported
        -  no failure is reported
        -  no test case are skipped
        -  number of test run equal to len of parameters set
        """
        self.init.create_communication_pipeline(3)
        parameters = [
            (1, 1, self.init.auxiliaries),
            (1, 2, [self.init.auxiliaries[0]]),
            (2, 3, [self.init.auxiliaries[1]]),
            (1, 4, [self.init.auxiliaries[2]]),
            (0, 5, self.init.auxiliaries[0:2]),
        ]

        for params in parameters:
            self.init.prepare_default_test_cases(params)
            self.init.prepare_remote_test_cases(params)

        runner = unittest.TextTestRunner()
        result = runner.run(self.init.suite)
        self.init.stop()

        self.assertEqual(result.wasSuccessful(), True)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(len(result.failures), 0)
        self.assertEqual(len(result.skipped), 0)
        self.assertEqual(result.testsRun, len(parameters * 2))


@pytest.mark.parametrize(
    "suite_id, case_id, aux_list, test_ids, tag, setup_timeout",
    [
        (
            1,
            1,
            None,
            {"Component1": ["Req1", "Req2"]},
            None,
            None,
        ),
        (
            1,
            2,
            ["aux2"],
            {"Component1": ["Req1", "Req2"]},
            None,
            None,
        ),
        (
            1,
            3,
            ["aux3"],
            {"Component1": ["Req1", "Req2"]},
            None,
            None,
        ),
        (
            1,
            4,
            ["aux4"],
            {"Component1": ["Req1", "Req2"]},
            None,
            None,
        ),
        (
            1,
            5,
            ["aux5", "aux6"],
            {"Component1": ["Req1", "Req2"]},
            None,
            5,
        ),
        (1, 5, ["aux1"], None, None, None),
        (1, 5, ["aux1"], {"Component1": ["Req1"]}, {"variant": ["variant1"]}, 10),
    ],
)
def test_define_test_parameters_on_basic_tc(
    suite_id,
    case_id,
    aux_list,
    test_ids,
    tag,
    setup_timeout,
    caplog,
):
    @test_case.define_test_parameters(
        suite_id=suite_id,
        case_id=case_id,
        aux_list=aux_list,
        test_ids=test_ids,
        tag=tag,
        setup_timeout=setup_timeout,
    )
    class MyClass(test_case.BasicTest):
        pass

    tc_inst = MyClass()

    assert tc_inst.test_suite_id == suite_id
    assert tc_inst.test_case_id == case_id
    aux_list = aux_list or []
    assert tc_inst.test_auxiliary_list == aux_list

    if setup_timeout is not None:
        with caplog.at_level(logging.INTERNAL_WARNING):
            assert "BasicTest does not support test timeouts, it will be discarded" in caplog.text

    assert tc_inst.test_ids == test_ids
    assert tc_inst.tag == tag


@pytest.mark.parametrize(
    "suite_id, case_id, aux_list, setup_timeout, run_timeout, teardown_timeout, test_ids, tag",
    [
        (1, 1, None, 1, 2, 3, {"Component1": ["Req1", "Req2"]}, None),
        (1, 2, ["aux2"], None, 2, 3, {"Component1": ["Req1", "Req2"]}, None),
        (1, 3, ["aux3"], 1, None, 3, {"Component1": ["Req1", "Req2"]}, None),
        (1, 4, ["aux4"], 1, 2, None, {"Component1": ["Req1", "Req2"]}, None),
        (
            1,
            5,
            ["aux5", "aux6"],
            None,
            None,
            None,
            {"Component1": ["Req1", "Req2"]},
            None,
        ),
        (1, 5, ["aux1"], None, None, None, None, None),
        (
            1,
            5,
            ["aux1"],
            1,
            2,
            3,
            {"Component1": ["Req1"]},
            {"variant": ["variant1"]},
        ),
    ],
)
def test_define_test_parameters_on_remote_tc(
    suite_id,
    case_id,
    aux_list,
    setup_timeout,
    run_timeout,
    teardown_timeout,
    test_ids,
    tag,
):
    @test_case.define_test_parameters(
        suite_id=suite_id,
        case_id=case_id,
        aux_list=aux_list,
        setup_timeout=setup_timeout,
        run_timeout=run_timeout,
        teardown_timeout=teardown_timeout,
        test_ids=test_ids,
        tag=tag,
    )
    class MyClass(test_case.RemoteTest):
        pass

    tc_inst = MyClass()
    assert tc_inst.test_suite_id == suite_id
    assert tc_inst.test_case_id == case_id
    aux_list = aux_list or []
    assert tc_inst.test_auxiliary_list == aux_list

    timeout_value = setup_timeout or tc_inst.response_timeout
    assert tc_inst.setup_timeout == timeout_value
    timeout_value = run_timeout or tc_inst.response_timeout
    assert tc_inst.run_timeout == timeout_value
    timeout_value = teardown_timeout or tc_inst.response_timeout
    assert tc_inst.teardown_timeout == timeout_value
    assert tc_inst.test_ids == test_ids
    assert tc_inst.tag == tag


@pytest.mark.parametrize(
    "max_try, rerun_setup, rerun_teardown, stability_test, expected_exception, expected_run_count, expected_setup_count, expected_teardown_count",
    [
        (
            5,
            True,
            True,
            False,
            None,
            3,
            2,
            2,
        ),
        (
            3,
            True,
            True,
            False,
            None,
            3,
            2,
            2,
        ),
        (
            3,
            True,
            False,
            False,
            None,
            3,
            2,
            0,
        ),
        (
            3,
            False,
            False,
            False,
            None,
            3,
            0,
            0,
        ),
        (
            2,
            True,
            True,
            False,
            Exception,
            2,
            1,
            1,
        ),
        (
            2,
            True,
            False,
            False,
            Exception,
            2,
            1,
            0,
        ),
        (
            5,
            True,
            True,
            True,
            None,
            5,
            4,
            4,
        ),
        (
            10,
            True,
            True,
            True,
            Exception,
            6,
            5,
            5,
        ),
    ],
)
def test_retry_on_failure_decorator(
    max_try,
    rerun_setup,
    rerun_teardown,
    stability_test,
    expected_exception,
    expected_run_count,
    expected_setup_count,
    expected_teardown_count,
    mocker,
    caplog,
):
    mock_test_case_class = mocker.Mock()

    if not stability_test:
        mock_test_case_class.test_run.side_effect = [
            Exception("try again"),
            Exception("try harder"),
            "bingo",
        ]
    else:
        mock_test_case_class.test_run.side_effect = list(range(5)) + [Exception("Exception")]
    # fix __name__ for the mock.test_run
    mock_test_case_class.test_run.__name__ = "test_run"
    mock_test_case_class._testMethodName = "test_run"

    partial_test_run = partial(
        retry_test_case(max_try, rerun_setup, rerun_teardown, stability_test)(mock_test_case_class.test_run)
    )
    if expected_exception:
        with pytest.raises(expected_exception):
            assert partial_test_run(mock_test_case_class)
            assert "Mock.test_run failed with exception: try again" in caplog.text
    else:
        partial_test_run(mock_test_case_class)

    assert mock_test_case_class.setUp.call_count == expected_setup_count
    assert mock_test_case_class.test_run.call_count == expected_run_count
    assert mock_test_case_class.tearDown.call_count == expected_teardown_count


def test_retry_on_failure_decorator_step_report(mocker):
    max_try = 3
    mock_test_case_class = mocker.Mock()
    mock_test_case_class.test_run.__name__ = "test_run"
    mock_test_case_class._testMethodName = "test_run"
    mock_test_case_class.step_report = step_report.StepReportData()
    mock_test_case_class.step_report.header = OrderedDict({"ITF version": "pykiso.__version__"})
    all_step_report_mock = {type(mock_test_case_class).__name__: {"succeed": True}}
    step_report.ALL_STEP_REPORT = all_step_report_mock
    prepare_report_mock = mocker.patch("pykiso.test_result.assert_step_report._prepare_report")
    add_retry_mocker = mocker.patch("pykiso.test_result.assert_step_report.add_retry_information")
    mock_test_case_class.test_run.side_effect = [
        Exception("try again"),
        Exception("try harder"),
        "bingo",
    ]

    partial_test_run = partial(retry_test_case(max_try, False, False, False)(mock_test_case_class.test_run))

    partial_test_run(mock_test_case_class)

    prepare_report_mock.assert_called_once_with(mock_test_case_class, "test_run")
    assert add_retry_mocker.call_count == 2


@pytest.mark.parametrize(
    "test_key,req_id, properties",
    [("ABC-12345", "ABC-req-12345", {}), ("dummy_test_key", "dummy_req_id", {"test_summary": "Dummy summary"})],
)
def test_xray_decorator(test_key, req_id, properties, mocker):
    mock_test_case_class = mocker.Mock()

    # fix __name__ for the mock.test_run
    mock_test_case_class.test_run.__name__ = "test_run"
    mock_test_case_class._testMethodName = "test_run"
    mock_test_case_class.properties = properties

    partial_test_run = partial(xray(test_key, req_id)(mock_test_case_class.test_run))

    partial_test_run(mock_test_case_class)

    assert isinstance(mock_test_case_class.properties, dict)

    assert mock_test_case_class.test_run.call_count == 1
    assert mock_test_case_class.properties["test_key"] == test_key
    assert mock_test_case_class.properties["req_id"] == req_id

    del mock_test_case_class.properties

    assert getattr(mock_test_case_class, "properties", None) is None


@pytest.mark.parametrize("properties,value, type", [("dummy1", "dummy2", str), ({}, {"dummy": 1}, dict)])
def test_properties(value, type, properties):
    class DummyClass(test_case.BasicTest):
        pass

    test_case_inst = DummyClass(1, 1, None, {"Component1": ["Req1", "Req2"]}, None, None, None, None)
    assert test_case_inst.properties is None

    # update properties
    test_case_inst.properties = properties
    assert isinstance(test_case_inst.properties, type)

    # update properties
    test_case_inst.properties = value
    assert isinstance(test_case_inst.properties, type)

    assert getattr(test_case_inst, "properties") == value

    # delete properties
    del test_case_inst.properties
    assert getattr(test_case_inst, "properties", None) is None
