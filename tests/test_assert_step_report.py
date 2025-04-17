import inspect
import pathlib
import sys
from collections import OrderedDict
from unittest import mock
from unittest.case import TestCase, _SubTest

import jinja2
import pytest

import pykiso.test_result.assert_step_report as assert_step_report
from pykiso import message
from pykiso.test_coordinator.test_case import RemoteTest
from pykiso.test_result.text_result import BannerTestResult
from pykiso.test_result.xml_result import TestInfo, XmlTestResult

# prevent pytest from collecting these as test cases
RemoteTest.__test__ = False
_SubTest.__test__ = False


@pytest.fixture
def test_case():
    tc = TestCase()
    # decorate 2 different assert
    tc.assertTrue = assert_step_report.assert_decorator(tc.assertTrue)
    tc.assertAlmostEqual = assert_step_report.assert_decorator(tc.assertAlmostEqual)

    # Add the step-report parameters
    tc.step_report = assert_step_report.StepReportData(header={}, message="", success=True, current_table=None)

    return tc


@pytest.fixture
def remote_test_case(mocker):
    class FakeReport:
        sub_type = message.MessageReportType.TEST_PASS

        def get_message_type(self):
            return message.MessageType.REPORT

    # auxiliary will be used in pykiso.test_execution.test_message_handler
    mock_auxiliary = mock.MagicMock()
    mock_auxiliary.send_fixture_command.return_value = True
    mock_auxiliary.wait_and_get_report.return_value = FakeReport()

    tc = RemoteTest(1, 2, [mock_auxiliary], 3, 4, 5, None, None)

    # decorate assertion performed in test_app_interaction
    tc.assertEqual = assert_step_report.assert_decorator(tc.assertEqual)

    # Add the step-report parameters
    tc.step_report = assert_step_report.StepReportData(header={}, message="", success=True, current_table=None)
    return tc


@pytest.fixture
def test_result():
    result = mock.MagicMock(spec=BannerTestResult(sys.stderr, False, 0))

    test1 = TestCase()
    test1.start_time = 1
    test1.stop_time = 2
    test1.elapsed_time = 1

    subtest = _SubTest(test1, "msg", None)

    test2 = mock.MagicMock(TestInfo)
    test2.start_time = 1
    test2.stop_time = 2
    test2.elapsed_time = 1
    test2.test_name = "x.TestClassName"
    test2.test_result = mock.MagicMock()
    test2.test_result.start_time = 1
    test2.test_result.stop_time = 2
    test2.test_result.elapsed_time = 1
    test2.test_id = "test.class_name.test_method_name"

    test3 = TestCase()
    test3.start_time = 1
    test3.stop_time = 2
    test3.elapsed_time = 1

    result.successes = [test1, (subtest,), test2]
    result.expectedFailures = []
    result.failures = [(test2, "")]
    result.errors = [(test3, "")]
    result.unexpectedSuccesses = []
    return result


def test_assert_decorator_no_message(mocker, test_case):
    step_result = mocker.patch("pykiso.test_result.assert_step_report._add_step")

    data_to_test = True
    test_case.assertTrue(data_to_test)

    step_result.assert_called_once_with(
        "TestCase",
        "test_assert_decorator_no_message",
        "",
        "data_to_test",
        "True",
        data_to_test,
        "NoneType: None\n",
    )


def test_assert_decorator_step_report_message(mocker, test_case):
    step_result = mocker.patch("pykiso.test_result.assert_step_report._add_step")

    test_case.step_report.message = "Dummy message"
    data_to_test = True
    test_case.assertTrue(data_to_test)

    assert test_case.step_report.message == ""
    step_result.assert_called_once_with(
        "TestCase",
        "test_assert_decorator_step_report_message",
        "Dummy message",
        "data_to_test",
        "True",
        data_to_test,
        "NoneType: None\n",
    )


def test_assert_decorator_reraise(mocker, test_case):
    step_result = mocker.patch("pykiso.test_result.assert_step_report._add_step")
    assert_step_report.ALL_STEP_REPORT = OrderedDict()
    assert_step_report.ALL_STEP_REPORT["TestCase"] = {
        "test_list": {"test_assert_decorator_reraise": {"steps": [[{"succeed": True}]]}}
    }

    data_to_test = False
    with pytest.raises(AssertionError, match="False is not true : Dummy message"):
        test_case.assertTrue(data_to_test, msg="Dummy message")

    assert (
        assert_step_report.ALL_STEP_REPORT["TestCase"]["test_list"]["test_assert_decorator_reraise"]["steps"][-1][-1][
            "succeed"
        ]
        == False
    )
    step_result.assert_called_once_with(
        "TestCase",
        "test_assert_decorator_reraise",
        "Dummy message",
        "data_to_test",
        "True",
        data_to_test,
        "NoneType: None\n",
    )


def test_assert_decorator_remote_test(mocker, remote_test_case):
    step_result = mocker.patch("pykiso.test_result.assert_step_report._add_step")

    remote_test_case.test_run()

    step_result.assert_called_once_with(
        "RemoteTest",
        "test_run",
        "",
        "report",
        "Equal to MessageReportType.TEST_PASS",
        message.MessageReportType.TEST_PASS,
        "NoneType: None\n",
    )


def test_assert_decorator_no_var_name(mocker, test_case):
    step_result = mocker.patch("pykiso.test_result.assert_step_report._add_step")

    test_case.assertTrue(True)

    step_result.assert_called_once_with(
        "TestCase",
        "test_assert_decorator_no_var_name",
        "",
        "True",
        "True",
        True,
        "NoneType: None\n",
    )


def test_assert_decorator_index_error(mocker, test_case):
    step_result = mocker.patch("pykiso.test_result.assert_step_report._add_step")
    mocked_get_variable_name = mocker.patch(
        "pykiso.test_result.assert_step_report._get_variable_name",
        side_effect=[IndexError("mocked error"), "some_var_name"],
    )
    test_case.assertTrue(True)

    step_result.assert_called_once()


def test_assert_decorator_multi_input(mocker, test_case):
    step_result = mocker.patch("pykiso.test_result.assert_step_report._add_step")

    data_to_test = 4.5
    data_expected = 4.5
    test_case.assertAlmostEqual(data_to_test, data_expected, delta=1, msg="Test the step report")

    step_result.assert_called_once_with(
        "TestCase",
        "test_assert_decorator_multi_input",
        "Test the step report",
        "data_to_test",
        "Almost Equal to 4.5; with delta=1",
        4.5,
        "NoneType: None\n",
    )


def test_generate(mocker, test_result):
    assert_step_report.ALL_STEP_REPORT = OrderedDict()
    assert_step_report.ALL_STEP_REPORT["TestClassName"] = OrderedDict()
    assert_step_report.ALL_STEP_REPORT["TestClassName"]["time_result"] = OrderedDict()
    assert_step_report.ALL_STEP_REPORT["TestClassName"]["time_result"]["Start Time"] = 1
    assert_step_report.ALL_STEP_REPORT["TestClassName"]["time_result"]["End Time"] = 2
    assert_step_report.ALL_STEP_REPORT["TestClassName"]["time_result"]["Elapsed Time"] = 1

    jinja2.FileSystemLoader = mock_loader = mock.MagicMock()
    jinja2.Environment = mock_environment = mock.MagicMock()

    mock_path = mock.MagicMock()
    mocker.patch.object(pathlib.Path, "resolve", return_value=mock_path)

    assert_step_report.generate_step_report(test_result, "step_report.html")

    mock_path.parent.mkdir.assert_called_once()


def test_add_step():
    assert_step_report.ALL_STEP_REPORT["TestCase"] = OrderedDict()
    assert_step_report.ALL_STEP_REPORT["TestCase"]["test_list"] = OrderedDict()
    assert_step_report.ALL_STEP_REPORT["TestCase"]["test_list"]["test_assert_step_report_multi_input"] = {}
    steplist = assert_step_report.ALL_STEP_REPORT["TestCase"]["test_list"]["test_assert_step_report_multi_input"][
        "steps"
    ] = [[]]

    assert_step_report._add_step(
        "TestCase",
        "test_assert_step_report_multi_input",
        "Test the step report",
        "data_to_test",
        "Almost Equal to 4.5; with delta=1",
        4.5,
        "None",
    )


def test_is_test_success():
    test_ok = {
        "steps": [[{"succeed": True}, {"succeed": True}, {"succeed": True}]],
        "unexpected_errors": [[]],
    }
    test_fail = {
        "steps": [[{"succeed": True}, {"succeed": False}, {"succeed": True}]],
        "unexpected_errors": [[]],
    }
    test_fail_error = {
        "steps": [[{"succeed": True}, {"succeed": True}, {"succeed": True}]],
        "unexpected_errors": [["error"]],
    }

    assert assert_step_report.is_test_success(test_ok)
    assert assert_step_report.is_test_success(test_fail) is False
    assert assert_step_report.is_test_success(test_fail_error) is False


@pytest.mark.parametrize(
    "parent_method",
    [
        "setUp",
        "tearDown",
        "handle_interaction",
        "test_run",
        "test_whaou",
    ],
)
def test_determine_parent_test_function(mocker, parent_method):
    frame = inspect.FrameInfo(
        "frame",
        "filename",
        "lineno",
        parent_method,
        "code_context",
        "index",
    )
    mocker.patch.object(inspect, "stack", return_value=[frame])

    function = assert_step_report.determine_parent_test_function("whaou_function")

    assert function == parent_method


@pytest.mark.parametrize(
    "function_name",
    [
        "setUp",
        "tearDown",
        "handle_interaction",
        "test_whaou",
    ],
)
def test_determine_parent_test_function_with_test_function(function_name):
    function = assert_step_report.determine_parent_test_function(function_name)

    assert function == function_name


@pytest.mark.parametrize("result_test", (False, True))
def test_add_retry_information(mocker, result_test):
    max_try = 3
    retry_nb = 2
    format_exec_mock = mocker.patch("traceback.format_exc", return_value="error_info")
    mock_test_case_class = mocker.Mock()
    mock_test_case_class.test_run.__name__ = "test_run"
    mock_test_case_class._testMethodName = "test_run"
    all_step_report_mock = {
        type(mock_test_case_class).__name__: {
            "test_list": {
                "test_run": {
                    "steps": [[{"succeed": False}, {"succeed": True}]],
                    "unexpected_errors": [[]],
                }
            },
            "succeed": True,
        }
    }
    assert_step_report.ALL_STEP_REPORT = all_step_report_mock

    assert_step_report.add_retry_information(mock_test_case_class, result_test, retry_nb, max_try, ValueError)

    test_info = assert_step_report.ALL_STEP_REPORT[type(mock_test_case_class).__name__]["test_list"]["test_run"]
    assert test_info["steps"] == [
        [{"succeed": False}, {"succeed": True}],
        [],
    ]
    assert test_info["unexpected_errors"] == [
        ["error_info"],
        [],
    ]
    assert test_info["max_try"] == max_try
    assert test_info["number_try"] == retry_nb + 1

    assert assert_step_report.ALL_STEP_REPORT[type(mock_test_case_class).__name__]["succeed"] == result_test
    format_exec_mock.assert_called_once()


def test_assert_decorator_step_report_message_deprecated(mocker, remote_test_case):
    step_result = mocker.patch("pykiso.test_result.assert_step_report._add_step")
    remote_test_case.assertEquals = assert_step_report.assert_decorator(remote_test_case.assertEquals)

    var = "Test"
    expected_var = "Test"
    remote_test_case.assertEquals(var, expected_var, "not expected str")

    assert step_result.call_count == 1
    step_result.assert_called_once_with(
        "RemoteTest",
        "test_assert_decorator_step_report_message_deprecated",
        "not expected str",
        "var",
        "Equals to Test",
        "Test",
        "NoneType: None\n",
    )


def test_assert_decorator_step_report_assert_called_in_unittest(mocker, remote_test_case):
    step_result = mocker.patch("pykiso.test_result.assert_step_report._add_step")
    remote_test_case.assertEqual = assert_step_report.assert_decorator(remote_test_case.assertEqual)
    remote_test_case.assertMultiLineEqual = assert_step_report.assert_decorator(remote_test_case.assertMultiLineEqual)
    remote_test_case.assertIsInstance = assert_step_report.assert_decorator(remote_test_case.assertIsInstance)

    var = "Test"
    expected_var = "Test"
    remote_test_case.assertEqual(var, expected_var, "not expected str")

    assert step_result.call_count == 1
    step_result.assert_called_once_with(
        "RemoteTest",
        "test_assert_decorator_step_report_assert_called_in_unittest",
        "not expected str",
        "var",
        "Equal to Test",
        "Test",
        "NoneType: None\n",
    )


@pytest.mark.parametrize(
    "timestamp, expected_date",
    [
        (1638316800, "01/12/21 00:00:00"),
        (1609459200, "01/01/21 00:00:00"),
    ],
)
def test_parse_timestamp(timestamp, expected_date):
    assert assert_step_report._parse_timestamp(timestamp) == expected_date


@pytest.mark.parametrize(
    "test_data, expected_result",
    [
        (
            {"steps": [[{"succeed": True}, {"succeed": True}, {"succeed": True}]], "unexpected_errors": [[]]},
            True,
        ),
        (
            {"steps": [[{"succeed": True}, {"succeed": False}, {"succeed": True}]], "unexpected_errors": [[]]},
            False,
        ),
        (
            {"steps": [[{"succeed": True}, {"succeed": True}, {"succeed": True}]], "unexpected_errors": [["error"]]},
            False,
        ),
        (
            {"steps": [[]], "unexpected_errors": [[]]},
            True,
        ),
    ],
)
def test_is_test_success_parametrized(test_data, expected_result):
    assert assert_step_report.is_test_success(test_data) == expected_result


def test_prepare_report_creates_test_class_entry(test_case):
    test_name = "test_method"
    assert_step_report._prepare_report(test_case, test_name)

    test_class_name = type(test_case).__name__
    assert test_class_name in assert_step_report.ALL_STEP_REPORT
    assert "header" in assert_step_report.ALL_STEP_REPORT[test_class_name]
    assert "description" in assert_step_report.ALL_STEP_REPORT[test_class_name]
    assert "file_path" in assert_step_report.ALL_STEP_REPORT[test_class_name]
    assert "time_result" in assert_step_report.ALL_STEP_REPORT[test_class_name]
    assert "test_list" in assert_step_report.ALL_STEP_REPORT[test_class_name]


def test_prepare_report_creates_test_method_entry(test_case):
    test_name = "test_method"
    assert_step_report._prepare_report(test_case, test_name)

    test_class_name = type(test_case).__name__
    assert test_name in assert_step_report.ALL_STEP_REPORT[test_class_name]["test_list"]
    assert "description" in assert_step_report.ALL_STEP_REPORT[test_class_name]["test_list"][test_name]
    assert "steps" in assert_step_report.ALL_STEP_REPORT[test_class_name]["test_list"][test_name]
    assert "unexpected_errors" in assert_step_report.ALL_STEP_REPORT[test_class_name]["test_list"][test_name]


def test_prepare_report_does_not_override_existing_entries(test_case):
    test_name = "test_method"
    assert_step_report._prepare_report(test_case, test_name)

    test_class_name = type(test_case).__name__
    initial_header = assert_step_report.ALL_STEP_REPORT[test_class_name]["header"]
    initial_description = assert_step_report.ALL_STEP_REPORT[test_class_name]["description"]

    assert_step_report._prepare_report(test_case, test_name)

    assert assert_step_report.ALL_STEP_REPORT[test_class_name]["header"] == initial_header
    assert assert_step_report.ALL_STEP_REPORT[test_class_name]["description"] == initial_description


def test_add_step_success():
    test_class_name = "TestClass"
    test_name = "test_method"
    message = "Test message"
    var_name = "var"
    expected = "Expected value"
    received = "Received value"
    failure_log = "None"

    assert_step_report.ALL_STEP_REPORT[test_class_name] = OrderedDict()
    assert_step_report.ALL_STEP_REPORT[test_class_name]["test_list"] = OrderedDict()
    assert_step_report.ALL_STEP_REPORT[test_class_name]["test_list"][test_name] = {"steps": [[]]}

    assert_step_report._add_step(
        test_class_name,
        test_name,
        message,
        var_name,
        expected,
        received,
        failure_log,
    )

    step = assert_step_report.ALL_STEP_REPORT[test_class_name]["test_list"][test_name]["steps"][-1][-1]
    assert step["message"] == message
    assert step["var_name"] == var_name
    assert step["expected_result"] == expected
    assert step["actual_result"] == received
    assert step["succeed"] is True
    assert step["failure_log"] == failure_log


@pytest.fixture
def mock_test_result(mocker):
    """Fixture to create a mock test result."""
    mock_result = mocker.MagicMock()
    mock_result.successes = []
    mock_result.expectedFailures = []
    mock_result.failures = []
    mock_result.errors = []
    mock_result.unexpectedSuccesses = []
    mock_result.stream.writeln = mocker.MagicMock()
    return mock_result


def test_generate_step_report_successful_tests(mocker, mock_test_result):
    """Test generate_step_report with successful tests."""
    mock_test_case = mocker.MagicMock(spec=TestCase)
    mock_test_case.start_time = 1638316800
    mock_test_case.stop_time = 1638316860
    mock_test_case.elapsed_time = 60
    mock_test_case._testMethodName = "test_success"
    mock_test_result.successes = [mock_test_case]

    mock_template = mocker.MagicMock()
    mock_template.render.return_value = "Rendered HTML"
    mock_environment = mocker.MagicMock()
    mock_environment.get_template.return_value = mock_template
    mocker.patch("jinja2.Environment", return_value=mock_environment)

    mock_output_file = mocker.MagicMock()
    mock_output_file.open = mocker.mock_open()
    mocker.patch("pathlib.Path.resolve", return_value=mock_output_file)

    assert_step_report.generate_step_report(mock_test_result, "output.html")

    mock_test_result.stream.writeln.assert_called_once_with("Generating HTML reports...")
    mock_environment.get_template.assert_called_once_with("templates/report_template.html.j2")
    mock_template.render.assert_called_once_with({"ALL_STEP_REPORT": assert_step_report.ALL_STEP_REPORT})
    mock_output_file.open.assert_called_once_with("w")


def test_generate_step_report_failed_tests(mocker, mock_test_result):
    """Test generate_step_report with failed tests."""
    mock_test_case = mocker.MagicMock(spec=TestCase)
    mock_test_case.start_time = 1638316800
    mock_test_case.stop_time = 1638316860
    mock_test_case.elapsed_time = 60
    mock_test_case._testMethodName = "test_failure"
    mock_test_result.failures = [(mock_test_case, "Failure message")]

    mock_template = mocker.MagicMock()
    mock_template.render.return_value = "Rendered HTML"
    mock_environment = mocker.MagicMock()
    mock_environment.get_template.return_value = mock_template
    mocker.patch("jinja2.Environment", return_value=mock_environment)

    mock_output_file = mocker.MagicMock()
    mock_output_file.open = mocker.mock_open()
    mocker.patch("pathlib.Path.resolve", return_value=mock_output_file)

    assert_step_report.generate_step_report(mock_test_result, "output.html")

    mock_test_result.stream.writeln.assert_called_once_with("Generating HTML reports...")
    mock_environment.get_template.assert_called_once_with("templates/report_template.html.j2")
    mock_template.render.assert_called_once_with({"ALL_STEP_REPORT": assert_step_report.ALL_STEP_REPORT})
    mock_output_file.open.assert_called_once_with("w")


def test_generate_step_report_with_errors(mocker, mock_test_result):
    """Test generate_step_report with errors."""
    mock_test_case = mocker.MagicMock(spec=TestCase)
    mock_test_case.start_time = 1638316800
    mock_test_case.stop_time = 1638316860
    mock_test_case.elapsed_time = 60
    mock_test_case._testMethodName = "test_error"
    mock_test_result.errors = [(mock_test_case, "Error message")]

    mock_template = mocker.MagicMock()
    mock_template.render.return_value = "Rendered HTML"
    mock_environment = mocker.MagicMock()
    mock_environment.get_template.return_value = mock_template
    mocker.patch("jinja2.Environment", return_value=mock_environment)

    mock_output_file = mocker.MagicMock()
    mock_output_file.open = mocker.mock_open()
    mocker.patch("pathlib.Path.resolve", return_value=mock_output_file)

    assert_step_report.generate_step_report(mock_test_result, "output.html")

    mock_test_result.stream.writeln.assert_called_once_with("Generating HTML reports...")
    mock_environment.get_template.assert_called_once_with("templates/report_template.html.j2")
    mock_template.render.assert_called_once_with({"ALL_STEP_REPORT": assert_step_report.ALL_STEP_REPORT})
    mock_output_file.open.assert_called_once_with("w")
