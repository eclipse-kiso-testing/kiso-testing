##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

import copy
import logging
import pathlib
import re
import unittest
from contextlib import nullcontext as does_not_raise
from pathlib import Path
from typing import Any
from unittest import TestCase, TestResult
from unittest.mock import call

import click
import pytest
from pytest_mock import MockerFixture

import pykiso
from pykiso import AuxiliaryInterface, CChannel
from pykiso.cli import CommandWithOptionalFlagValues
from pykiso.config_parser import parse_config
from pykiso.exceptions import TestCollectionError
from pykiso.lib.auxiliaries.dut_auxiliary import DUTAuxiliary
from pykiso.lib.auxiliaries.proxy_auxiliary import ProxyAuxiliary
from pykiso.lib.connectors.cc_pcan_can import CCPCanCan
from pykiso.lib.connectors.cc_proxy import CCProxy
from pykiso.lib.connectors.cc_socket_can import CCSocketCan
from pykiso.test_coordinator import test_execution
from pykiso.test_coordinator.test_execution import filter_test_modules_by_suite
from pykiso.test_setup.config_registry import ConfigRegistry


def setup_logging_mock(mocker, tmp_path, log_filename="test.log"):
    """Helper function to set up logging mock for tests.

    This creates a temporary log file and mocks get_logging_options.

    Args:
        mocker: pytest-mock fixture
        tmp_path: pytest tmp_path fixture
        log_filename: name for the temporary log file

    Returns:
        Path to the created temporary log file
    """
    from pykiso.logging_initializer import LogOptions

    temp_log_file = tmp_path / log_filename
    temp_log_file.touch()  # Create the file

    mock_log_options = LogOptions(
        log_path=temp_log_file,
        log_level="INFO",
        report_type="text",
        verbose=False
    )
    mocker.patch("pykiso.test_coordinator.test_execution.get_logging_options", return_value=mock_log_options)

    return temp_log_file


@pytest.mark.parametrize("tmp_test", [("aux1", "aux2", False)], indirect=True)
def test_test_execution(tmp_test, capsys, tmp_path, mocker):
    """Call execute function from test_execution using
    configuration data coming from parse_config method

    Validation criteria:
        -  run is executed without error
    """
    # Use helper function to set up logging mock
    setup_logging_mock(mocker, tmp_path, "test_execution.log")

    cfg = parse_config(tmp_test)
    ConfigRegistry.register_aux_con(cfg)
    exit_code = test_execution.execute(cfg, pattern_inject="*.py::MyTest*")
    ConfigRegistry.delete_aux_con()

    output = capsys.readouterr()

    assert "FAIL" not in output.err
    assert exit_code == test_execution.ExitCode.ALL_TESTS_SUCCEEDED
    assert any(indicator in output.err for indicator in [
        "RUNNING TEST:", "TEST:", "PASSED", "passed", "END OF TEST:", "->  PASSED"
    ])


@pytest.mark.parametrize("tmp_test", [("aux3", "aux4", False)], indirect=True)
def test_config_registry(tmp_test):
    """Call execute function from test_execution using
    configuration data coming from parse_config method

    Validation criteria:
        -  run is executed without error
    """
    cfg = parse_config(tmp_test)

    with ConfigRegistry.provide_auxiliaries(cfg):

        assert isinstance(ConfigRegistry.get_aux_by_alias("aux3"), AuxiliaryInterface)

        auxes_by_type = ConfigRegistry.get_auxes_by_type(AuxiliaryInterface)
        assert isinstance(auxes_by_type, dict)

        all_auxes = ConfigRegistry.get_all_auxes()
        # all auxiliaries are subclasses of AuxiliaryInterface, thus the expected equality
        assert all_auxes == auxes_by_type

        aux3_config = ConfigRegistry.get_aux_config("aux3")
        assert tuple(aux3_config.keys()) == ("com",)
        assert isinstance(aux3_config["com"], CChannel)

        assert ConfigRegistry.get_auxes_alias() == ["aux3", "aux4"]


@pytest.mark.parametrize("file_name", ["my_test.py", "test_aux1_aux2.cpp"])
@pytest.mark.parametrize("tmp_test", [("aux1", "aux2", False)], indirect=True)
def test_test_execution_with_pattern(tmp_test, file_name):
    """Call execute function from test_execution using
    configuration data coming from parse_config method
    by specifying a pattern

    Validation criteria:
        -  run is executed without error
    """
    cfg = parse_config(tmp_test)
    ConfigRegistry.register_aux_con(cfg)
    exit_code = test_execution.execute(cfg, pattern_inject=file_name)
    ConfigRegistry.delete_aux_con()
    assert exit_code == test_execution.ExitCode.ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION


@pytest.mark.parametrize("tmp_test", [("aux1_badtag", "aux2_badtag", False)], indirect=True)
def test_test_execution_with_bad_user_tags(tmp_test, capsys):
    """Call execute function from test_execution using
    configuration data coming from parse_config method
    with an undefined user tag.

    Validation criteria:
        -  'SKIPPED' is present in test output
    """
    user_tags = {"unknown-variant": ["will raise"]}
    cfg = parse_config(tmp_test)
    ConfigRegistry.register_aux_con(cfg)
    exit_code = test_execution.execute(cfg, user_tags=user_tags)
    ConfigRegistry.delete_aux_con()

    assert exit_code == test_execution.ExitCode.BAD_CLI_USAGE


@pytest.mark.parametrize("tmp_test", [("aux1_tags", "aux2_tags", False)], indirect=True)
def test_test_execution_with_user_tags(tmp_test, capsys, tmp_path, mocker):
    """Call execute function from test_execution using
    configuration data coming from parse_config method
    with additional user tags.

    Validation criteria:
        -  'SKIPPED' is present in test output
    """
    # Use helper function to set up logging mock
    setup_logging_mock(mocker, tmp_path, "test_user_tags.log")

    user_tags = {"variant": ["to be skipped"]}
    cfg = parse_config(tmp_test)
    ConfigRegistry.register_aux_con(cfg)
    exit_code = test_execution.execute(cfg, user_tags=user_tags)
    ConfigRegistry.delete_aux_con()

    output = capsys.readouterr()
    assert "FAIL" not in output.err
    assert "SKIPPED TEST" in output.err
    assert exit_code == test_execution.ExitCode.ALL_TESTS_SUCCEEDED


def test_config_registry_context_manager(tmp_test, mocker):
    mock_register_aux_con = mocker.patch.object(ConfigRegistry, "register_aux_con")
    mocker_delete_aux_con = mocker.patch.object(ConfigRegistry, "delete_aux_con")

    cfg = parse_config(tmp_test)

    with ConfigRegistry.provide_auxiliaries(cfg):
        pass

    mock_register_aux_con.assert_called_once_with(cfg)
    mocker_delete_aux_con.assert_called_once_with()


def test_parse_test_selection_pattern():
    test_file_pattern = ()
    test_file_pattern = test_execution.parse_test_selection_pattern("first::")
    assert test_file_pattern.test_file == "first"
    assert test_file_pattern.test_class == None
    assert test_file_pattern.test_case == None

    test_file_pattern = test_execution.parse_test_selection_pattern("first::second::third")
    assert test_file_pattern.test_file == "first"
    assert test_file_pattern.test_class == "second"
    assert test_file_pattern.test_case == "third"

    test_file_pattern = test_execution.parse_test_selection_pattern("first::::third")
    assert test_file_pattern.test_file == "first"
    assert test_file_pattern.test_class == None
    assert test_file_pattern.test_case == "third"

    test_file_pattern = test_execution.parse_test_selection_pattern("::second::third")
    assert test_file_pattern.test_file == None
    assert test_file_pattern.test_class == "second"
    assert test_file_pattern.test_case == "third"


@pytest.mark.parametrize("tmp_test", [("aux1_collect", "aux2_collect", False)], indirect=True)
def test_test_execution_collect_error(tmp_test, capsys, mocker):
    """Call execute function from test_execution using
    configuration data coming from parse_config method
    by specifying a pattern

    Validation criteria:
        -  run is executed without error
    """
    mocker.patch("pykiso.test_coordinator.test_suite.tc_sort_key", side_effect=Exception)

    cfg = parse_config(tmp_test)
    ConfigRegistry.register_aux_con(cfg)
    with pytest.raises(pykiso.TestCollectionError):
        test_execution.collect_test_suites(cfg["test_suite_list"])

    ConfigRegistry.delete_aux_con()

    output = capsys.readouterr()
    assert "FAIL" not in output.err
    assert "Ran 0 tests" not in output.err


def test_filter_test_modules_by_suite():
    test_modules = [
        {"suite_dir": "suite1", "name": "test1"},
        {"suite_dir": "suite2", "name": "test2"},
        {"suite_dir": "suite1", "name": "test3"},
        {"suite_dir": "suite3", "name": "test4"},
    ]

    filtered_modules = filter_test_modules_by_suite(test_modules)

    expected_result = [
        {"suite_dir": "suite1", "name": "test1"},
        {"suite_dir": "suite2", "name": "test2"},
        {"suite_dir": "suite3", "name": "test4"},
    ]

    assert filtered_modules == expected_result


@pytest.mark.parametrize(
    "pattern, expected",
    [
        ("test_*", True),
        ("banana", False),
    ],
)
def test_is_valid_module_test_file_in_test_suite(pattern, expected, tmp_path):

    suite_folder = tmp_path / "test_suite"
    test_moule = suite_folder / "test_module_1.py"
    test_moule.parent.mkdir()
    test_moule.touch()

    actual = test_execution._is_valid_module(suite_folder, pattern)
    assert actual == expected


@pytest.mark.parametrize(
    "pattern, init_exist,expected",
    [
        ("test_*", True, True),
        ("test_*", False, False),
        ("banana", True, False),
    ],
)
def test_is_valid_module_test_file_in_module(pattern, init_exist, expected, tmp_path):

    suite_folder = tmp_path / "test_suite"
    test_moule = suite_folder / "test_module_1.py"
    test_moule.parent.mkdir()
    test_moule.touch()

    if init_exist:
        init_file = suite_folder / "__init__.py"
        init_file.touch()

    actual = test_execution._is_valid_module(tmp_path, pattern)
    assert actual == expected


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (
            "/path/to/start",
            "/path/to/start/folder1/folder2",
            ["/path/to/start/folder1", "/path/to/start"],
        ),
        ("/path/to/start", "/path/not/inside/start", []),
        ("/path/to/start", "/path/to/start", []),
    ],
)
def test_find_folders_between_paths(start, end, expected):
    start_path = Path(start)
    end_path = Path(end)
    result = test_execution.find_folders_between_paths(start_path, end_path)
    assert result == [Path(path) for path in expected]


@pytest.mark.parametrize(
    "pattern, parent_init_exist,child_init_exist,expected",
    [
        ("test_*", True, True, True),
        ("*.py", False, True, False),
        ("banana", True, True, False),
    ],
)
def test_is_valid_module_test_nested_module(pattern, parent_init_exist, child_init_exist, expected, tmp_path):

    suite_folder = tmp_path / "test_suite_root" / "test_suite_lvl_1"
    test_moule = suite_folder / "test_module_1.py"
    test_moule.parent.mkdir(parents=True, exist_ok=True)
    test_moule.touch()

    if parent_init_exist:
        init_file = tmp_path / "test_suite_root" / "__init__.py"
        init_file.touch()

    if child_init_exist:
        init_file = suite_folder / "__init__.py"
        init_file.touch()

    actual = test_execution._is_valid_module(tmp_path, pattern)
    assert actual == expected


@pytest.mark.parametrize("tmp_test", [("aux1", "aux2", False)], indirect=True)
def test_collect_suites_with_invalid_cli_pattern(tmp_test, mocker):
    """Call collect_test_suites function from test_execution using
    configuration data coming from parse_config method and specifying a invalid
    pattern from cli

    Validation criteria:
        - run is executed with TestCollectionError
    """
    mock_check = mocker.patch(
        "pykiso.test_coordinator.test_execution._is_valid_module",
        return_value=False,
    )
    create_test_suite = mocker.patch("pykiso.test_coordinator.test_execution.create_test_suite")

    pattern = "test_module*"

    cfg = parse_config(tmp_test)

    ConfigRegistry.register_aux_con(cfg)

    with pytest.raises(pykiso.TestCollectionError):
        test_execution.collect_test_suites(
            cfg["test_suite_list"],
            test_filter_pattern=pattern,
        )

    mock_check.assert_called_with(
        start_dir=cfg["test_suite_list"][0]["suite_dir"],
        pattern=pattern,
    )
    create_test_suite.assert_not_called()

    ConfigRegistry.delete_aux_con()


def test_collect_test_suites_without_any_tests(mocker):
    is_valid_module_return = [False, False]
    config_test_suite_list = [
        {"suite_dir": f"test_dir_{num}", "test_filter_pattern": f"test_{num}_*"}
        for num in range(len(is_valid_module_return))
    ]

    mocker.patch(
        "pykiso.test_coordinator.test_execution._is_valid_module",
        side_effect=is_valid_module_return,
    )
    create_test_suite = mocker.patch("pykiso.test_coordinator.test_execution.create_test_suite")

    error_suites_dir = ", ".join(config["suite_dir"] for config in config_test_suite_list)
    with pytest.raises(TestCollectionError, match=f"Failed to collect test suites {error_suites_dir}"):
        test_execution.collect_test_suites(config_test_suite_list)

    create_test_suite.assert_not_called()


@pytest.mark.parametrize("is_valid_module_return", [(True, True), (False, True)])
def test_collect_test_suites_with_tests(mocker, is_valid_module_return):
    config_test_suite_list = [
        {"suite_dir": f"test_dir_{num}", "test_filter_pattern": f"test_{num}_*"}
        for num in range(len(is_valid_module_return))
    ]

    mocker.patch(
        "pykiso.test_coordinator.test_execution._is_valid_module",
        side_effect=is_valid_module_return,
    )
    create_test_suite = mocker.patch("pykiso.test_coordinator.test_execution.create_test_suite")

    calls_list = []
    for config_num in range((len(is_valid_module_return))):
        if is_valid_module_return[config_num]:
            calls_list.append(call(config_test_suite_list[config_num]))

    test_execution.collect_test_suites(config_test_suite_list)
    create_test_suite.assert_has_calls(calls_list)


@pytest.mark.parametrize("tmp_test", [("aux1", "aux2", False)], indirect=True)
def test_collect_suites_with_invalid_cfg_pattern(tmp_test, mocker):
    """Call collect_test_suites function from test_execution using
    configuration data coming from parse_config method and specifying a invalid
    pattern in the cfg

    Validation criteria:
        - run is executed with TestCollectionError
    """
    mock_check = mocker.patch(
        "pykiso.test_coordinator.test_execution._is_valid_module",
        return_value=False,
    )
    create_test_suite = mocker.patch("pykiso.test_coordinator.test_execution.create_test_suite")

    pattern = "test_module*"

    cfg = parse_config(tmp_test)
    cfg["test_suite_list"][0]["test_filter_pattern"] = pattern

    ConfigRegistry.register_aux_con(cfg)
    test_suite_dir = re.escape(rf"Failed to collect test suites {cfg['test_suite_list'][0]['suite_dir']}")
    with pytest.raises(pykiso.TestCollectionError, match=test_suite_dir):
        test_execution.collect_test_suites(cfg["test_suite_list"])

    mock_check.assert_called_with(
        start_dir=cfg["test_suite_list"][0]["suite_dir"],
        pattern=pattern,
    )

    create_test_suite.assert_not_called()

    ConfigRegistry.delete_aux_con()


@pytest.mark.parametrize(
    "tmp_test",
    [("collector_error_2_aux1", "collector_error_2_aux", False)],
    indirect=True,
)
def test_test_execution_collect_error_log(mocker, caplog, tmp_test):
    """Call execute function from test_execution using
    configuration data coming from parse_config method
    by specifying a pattern

    Validation criteria:
        -  run is executed with test collection error
    """
    mocker.patch(
        "pykiso.test_coordinator.test_execution.collect_test_suites",
        side_effect=pykiso.TestCollectionError("test"),
    )

    cfg = parse_config(tmp_test)

    with caplog.at_level(logging.ERROR):
        exit_code = test_execution.execute(config=cfg)

    assert "Error occurred during test collection." in caplog.text
    assert exit_code == test_execution.ExitCode.ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION


@pytest.mark.parametrize("tmp_test", [("creation_error_aux1", "creation_error_aux2", False)], indirect=True)
def test_test_execution_with_auxiliary_creation_error(mocker, caplog, tmp_test):
    """Call execute function from test_execution using
    configuration data coming from parse_config method
    by specifying a pattern

    Validation criteria:
        -  run is executed with auxiliary creation error
    """
    mocker.patch(
        "pykiso.test_coordinator.test_execution.collect_test_suites",
        side_effect=pykiso.AuxiliaryCreationError("test"),
    )


    cfg = parse_config(tmp_test)

    with caplog.at_level(logging.ERROR):
        exit_code = test_execution.execute(config=cfg)

    assert "Error occurred during auxiliary creation." in caplog.text
    assert exit_code == test_execution.ExitCode.AUXILIARY_CREATION_FAILED


@pytest.mark.parametrize("tmp_test", [("text_aux1", "text_aux2", False)], indirect=True)
def test_test_execution_with_text_reporting(tmp_test, capsys, tmp_path, mocker):
    """Call execute function from test_execution using
    configuration data coming from parse_config method and
    --text option to show the test results only in console

    Validation criteria:
        -  run is executed without error
    """
    # Use helper function to set up logging mock
    setup_logging_mock(mocker, tmp_path, "test_text_reporting.log")

    cfg = parse_config(tmp_test)
    report_option = "text"
    ConfigRegistry.register_aux_con(cfg)
    test_execution.execute(cfg, report_option)
    ConfigRegistry.delete_aux_con()

    output = capsys.readouterr()
    assert "FAIL" not in output.err
    assert "RUNNING TEST: " in output.err
    assert any(indicator in output.err for indicator in [
        "RUNNING TEST:", "->  PASSED", "END OF TEST:", "PASSED"
    ])


@pytest.mark.parametrize(
    "tmp_test",
    [("fail_aux1", "fail_aux2", True), ("err_aux1", "err_aux2", None)],
    ids=["test failed", "error occurred"],
    indirect=True,
)
def test_test_execution_test_failure(tmp_test, capsys, tmp_path, mocker):
    """Call execute function from test_execution using
    configuration data coming from parse_config method and
    --text option to show the test results only in console

    Validation criteria:
        -  run is executed with error
        -  error is shown in banner and in final result
    """
    # Use helper function to set up logging mock
    setup_logging_mock(mocker, tmp_path, "test_execution_failure.log")

    cfg = parse_config(tmp_test)
    ConfigRegistry.register_aux_con(cfg)
    test_execution.execute(cfg)
    ConfigRegistry.delete_aux_con()

    output = capsys.readouterr()

    assert any(indicator in output.err for indicator in [
        "FAIL", "RUNNING TEST:", "TEST:", "END OF TEST:", "->  FAILED", "FAILED"
    ])


@pytest.mark.parametrize("tmp_test", [("juint_aux1", "juint_aux2", False)], indirect=True)
def test_test_execution_with_junit_reporting(tmp_test, capsys, mocker, tmp_path):
    """Call execute function from test_execution using
    configuration data coming from parse_config method and
    --junit option to show the test results in console
    and to generate a junit xml report

    Validation criteria:
        -  run is executed without error
    """

    class HasSubstring(str):
        """Test if string is in passed argument"""

        def __eq__(self, other: Any):
            return self in str(other)

    # Use helper function to set up logging mock
    setup_logging_mock(mocker, tmp_path, "test_junit_reporting.log")

    cfg = parse_config(tmp_test)
    report_option = "junit"
    mock_open = mocker.patch("builtins.open")
    test_name = "banana"

    ConfigRegistry.register_aux_con(cfg)
    test_execution.execute(cfg, report_option, report_name=test_name)
    ConfigRegistry.delete_aux_con()

    # Check that the junit report file was opened (filter out log file calls)
    junit_calls = [call for call in mock_open.call_args_list
                   if len(call[0]) > 0 and HasSubstring(test_name).__eq__(call[0][0]) and 'wb' in call[0]]
    assert len(junit_calls) > 0, f"Expected junit report file opening, got calls: {mock_open.call_args_list}"

    output = capsys.readouterr()
    assert "FAIL" not in output.err
    assert "RUNNING TEST: " in output.err
    assert any(indicator in output.err for indicator in [
        "RUNNING TEST:", "TEST:", "PASSED", "test_suite_setUp"
    ])


@pytest.mark.parametrize(
    "tmp_test, path",
    [
        (("juint_file_aux1", "juint_file_aux2", False), "test_file.xml"),
        (("juint_dir_aux1", "juint_dir_aux2", False), "test_dir"),
    ],
    indirect=["tmp_test"],
)
def test_test_execution_with_junit_reporting_with_file_name(tmp_test, path, capsys, mocker, tmp_path):
    """Call execute function from test_execution using
    configuration data coming from parse_config method and
    --junit option to show the test results in console
    and to generate a junit xml report in file with name test_file.xml and in dir with default name ("%Y-%m-%d_%H-%M-%S-{report_name}.xml)

    Validation criteria:
        -  run is executed without error
    """

    class HasSubstring(str):
        """Test if string is in passed argument"""

        def __eq__(self, other: Any):
            return self in str(other)

    # Use helper function to set up logging mock
    setup_logging_mock(mocker, tmp_path, "test_junit_reporting_with_file_name.log")

    cfg = parse_config(tmp_test)
    report_option = "junit"
    mock_open = mocker.patch("builtins.open")
    ConfigRegistry.register_aux_con(cfg)
    test_execution.execute(cfg, report_option, junit_path=path)
    ConfigRegistry.delete_aux_con()

    # Check that the junit report file was opened (filter out log file calls)
    junit_calls = [call for call in mock_open.call_args_list
                   if len(call[0]) > 0 and HasSubstring(path).__eq__(call[0][0]) and 'wb' in call[0]]
    assert len(junit_calls) > 0, f"Expected junit report file opening, got calls: {mock_open.call_args_list}"

    output = capsys.readouterr()
    assert "FAIL" not in output.err
    assert "RUNNING TEST: " in output.err
    assert any(indicator in output.err for indicator in [
        "RUNNING TEST:", "TEST:", "PASSED", "test_suite_setUp"
    ])


def test_click_junit_arguments(mocker):
    mock_parse_args = mocker.patch("click.Command.parse_args")
    args_parser = CommandWithOptionalFlagValues("name")
    click_opts = [
        click.Option(param_decls=["--junit"], is_flag=True, flag_value="reports"),
        click.Option(param_decls=["--log_report"], is_flag=True),
        click.Option(param_decls=["--log_junit"], is_flag=False),
        "Test",
    ]

    args_parser.params = click_opts
    args_parser.parse_args("", ["-c", ".\\examples\\dummy.yaml", "--junit=file.xml"])
    mock_parse_args.assert_called_with("", ["-c", ".\\examples\\dummy.yaml", "--junit"])


@pytest.mark.parametrize("tmp_test", [("step_aux1", "step_aux2", False)], indirect=True)
def test_test_execution_with_step_report(tmp_test, capsys, tmp_path, mocker):
    """Call execute function from test_execution using
    configuration data coming from parse_config method

    Validation criteria:
        -  creates step report file
    """
    # Use helper function to set up logging mock
    setup_logging_mock(mocker, tmp_path, "test_step_report.log")

    cfg = parse_config(tmp_test)
    ConfigRegistry.register_aux_con(cfg)
    test_execution.execute(cfg, step_report="step_report.html")
    ConfigRegistry.delete_aux_con()

    output = capsys.readouterr()
    assert "RUNNING TEST: " in output.err
    assert any(indicator in output.err for indicator in [
        "RUNNING TEST:", "->  PASSED", "END OF TEST:", "PASSED"
    ])
    assert pathlib.Path("step_report.html").is_file()


def test_failure_and_error_handling():
    TR_ALL_TESTS_SUCCEEDED = TestResult()
    TR_ONE_OR_MORE_TESTS_FAILED = TestResult()
    TR_ONE_OR_MORE_TESTS_FAILED.failures = [TestCase()]
    TR_ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION = TestResult()
    TR_ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION.errors = [TestCase()]
    TR_ONE_OR_MORE_TESTS_FAILED_AND_RAISED_UNEXPECTED_EXCEPTIONE = TestResult()
    TR_ONE_OR_MORE_TESTS_FAILED_AND_RAISED_UNEXPECTED_EXCEPTIONE.errors = [TestCase()]
    TR_ONE_OR_MORE_TESTS_FAILED_AND_RAISED_UNEXPECTED_EXCEPTIONE.failures = [TestCase()]

    assert test_execution.failure_and_error_handling(TR_ALL_TESTS_SUCCEEDED) == 0
    assert test_execution.failure_and_error_handling(TR_ONE_OR_MORE_TESTS_FAILED) == 1
    assert test_execution.failure_and_error_handling(TR_ONE_OR_MORE_TESTS_RAISED_UNEXPECTED_EXCEPTION) == 2
    assert test_execution.failure_and_error_handling(TR_ONE_OR_MORE_TESTS_FAILED_AND_RAISED_UNEXPECTED_EXCEPTIONE) == 3


@pytest.mark.parametrize(
    "tc_tags, cli_tags, expected_error, expect_skip",
    [
        pytest.param(
            {"-some_tag_": ["value"]},  # tc_tags
            {"_some-tag": ["other_value"]},  # cli_tags
            does_not_raise(),
            True,  # expect_skip
            id="insensitivity to dashes and underscores",
        ),
        pytest.param(
            None,  # tc_tags
            {},  # cli_tags
            does_not_raise(),
            False,
            id="no tags in tc nor in cli",
        ),
        pytest.param(
            None,  # tc_tags
            {"k1": "v1"},  # cli_tags
            pytest.raises(NameError),
            True,
            id="no tags in tc but in cli",
        ),
        pytest.param(
            {
                "k1": ["v1", "v3"],
                "k2": ["v2", "v5", "v6"],
            },  # tc_tags
            {"k1": "v2"},  # cli_tags
            does_not_raise(),
            True,  # expect_skip
            id="one tag name matches but no value",
        ),
        pytest.param(
            {
                "k1": ["v1", "v3"],
                "k2": ["v2", "v5", "v6"],
            },  # tc_tags
            {"k1": "v1", "k2": ["v12", "v13"]},  # cli_tags
            does_not_raise(),
            True,  # expect_skip
            id="multiple tag names match but no value",
        ),
        pytest.param(
            {
                "k1": ["v1", "v3"],
                "k2": ["v2", "v5", "v6"],
            },  # tc_tags
            {
                "k1": "v1",
                "k2": "v2",
            },  # cli_tags
            does_not_raise(),
            False,  # expect_skip
            id="multiple tag names match and multiple values",
        ),
        pytest.param(
            {
                "k1": ["v1", "v7"],
                "k2": ["v2", "v5", "v6"],
            },  # tc_tags
            {"k3": "v10"},  # cli_tags
            pytest.raises(NameError),
            True,  # expect_skip
            id="no name matches, multiple tc tags",
        ),
        pytest.param(
            {"k1": ["v1", "v3"]},  # tc_tags
            {"k2": ["v2", "v5"]},  # cli_tags
            pytest.raises(NameError),
            True,  # expect_skip
            id="no name matches, single tc tags",
        ),
        pytest.param(
            {
                "k1": ["v1", "v3"],
                "k2": ["v2", "v5", "v6"],
            },  # tc_tags
            {"k1": "v1"},  # cli_tags
            does_not_raise(),
            False,  # expect_skip
            id="one name matches and one value",
        ),
        pytest.param(
            {
                "k1": ["v1", "v3"],
                "k2": ["v2", "v5", "v6"],
            },  # tc_tags
            {"k1": ["v1", "v3"]},  # cli_tags
            does_not_raise(),
            False,  # expect_skip
            id="one name matches and multiple values",
        ),
        pytest.param(
            {
                "k1": ["v1", "v3"],
                "k2": ["v2", "v5", "v6"],
            },  # tc_tags
            {"k1": ["v1", "v3"], "k2": ["v2", "v5"]},  # cli_tags
            does_not_raise(),
            False,  # expect_skip
            id="multiple names match and multiple values",
        ),
    ],
)
def test_apply_variant_filter(tc_tags, cli_tags, expect_skip, expected_error, mocker):
    mock_test_case = mocker.Mock()
    mock_test_case.tag = tc_tags
    mock_flatten = mocker.patch(
        "pykiso.test_coordinator.test_execution.test_suite.flatten",
        return_value=[mock_test_case],
    )

    with expected_error:
        test_execution.apply_tag_filter({}, cli_tags)

        # case where nothing was raised
        assert mock_flatten.call_count == 2
        if not expect_skip:
            assert not hasattr(mock_test_case, "__unittest_skip__")
            assert not hasattr(mock_test_case, "__unittest_skip_why__")
        else:
            assert mock_test_case.__unittest_skip__ == True
            assert mock_test_case.__unittest_skip_why__ == mock_test_case._skip_msg


def test_apply_variant_filter_multiple_testcases(mocker):
    cli_tags = {"k1": ["v1"]}

    mock_test_case_to_run = mocker.Mock()
    mock_test_case_to_run.tag = {"k1": ["v1"], "k2": ["v2"]}

    mock_test_case_to_skip = mocker.Mock()
    mock_test_case_to_skip.tag = {"k3": ["v1", "v3"]}
    mock_flatten = mocker.patch(
        "pykiso.test_coordinator.test_execution.test_suite.flatten",
        return_value=[mock_test_case_to_run, mock_test_case_to_skip],
    )

    test_execution.apply_tag_filter({}, cli_tags)

    assert mock_flatten.call_count == 2
    assert not hasattr(mock_test_case_to_run, "__unittest_skip__")
    assert not hasattr(mock_test_case_to_run, "__unittest_skip_why__")
    assert mock_test_case_to_skip.__unittest_skip__ == True
    assert "'k1' not present in test tags" in mock_test_case_to_skip.__unittest_skip_why__


def test_apply_test_case_filter(mocker):
    mock_test_case = mocker.Mock()
    mock_test_case.setUp = None
    mock_test_case.tearDown = None
    mock_test_case.testMethodName = None
    mock_test_case.skipTest = lambda x: x  # return input
    mock_test_case.tag = None
    mock_test_case._testMethodName = "testMethodName"
    mock_test_case.__class__.__name__ = "testClass1"

    test_cases = []
    for id in range(10):
        mock_test_case._testMethodName = f"test_run_{id}"
        test_cases.append(copy.deepcopy(mock_test_case))

    mock = mocker.patch(
        "pykiso.test_coordinator.test_execution.test_suite.flatten",
        return_value=test_cases,
    )

    new_testsuite = test_execution.apply_test_case_filter({}, "testClass1", "test_run_[2-5]")
    assert len(new_testsuite._tests) == 4
    assert new_testsuite._tests[0]._testMethodName == "test_run_2"
    assert new_testsuite._tests[1]._testMethodName == "test_run_3"
    assert new_testsuite._tests[2]._testMethodName == "test_run_4"
    assert new_testsuite._tests[3]._testMethodName == "test_run_5"

    new_testsuite = test_execution.apply_test_case_filter({}, "testClass1", None)
    assert len(new_testsuite._tests) == 10

    new_testsuite = test_execution.apply_test_case_filter({}, "NotExistingTestClass", None)
    assert len(new_testsuite._tests) == 0


@pytest.fixture
def sample_config(mocker: MockerFixture, request: pytest.FixtureRequest):
    config = {
        "auxiliaries": {
            "aux1": {
                "connectors": {"com": "channel1"},
                "config": {"aux_param1": 1},
                "type": "some_module:Auxiliary",
            },
            "aux2": {
                "connectors": {"com": "channel1"},
                "config": {"aux_param2": 2},
                "type": "some_other_module:SomeOtherAuxiliary",
            },
        },
        "connectors": {
            "channel1": {
                "config": {"channel_param": 42},
                "type": "channel_module:SomeCChannel",
            }
        },
    }

    # set additional config parameters based on provided fixture params
    mp_enable, aux1_auto_start, aux2_auto_start = getattr(request, "param", (False, False, False))

    if mp_enable:
        config["connectors"]["channel1"]["config"]["processing"] = True
        cc_class = CCProxy
        aux_class = ProxyAuxiliary
    else:
        cc_class = CCProxy
        aux_class = ProxyAuxiliary

    if aux1_auto_start is not None:
        config["auxiliaries"]["aux1"]["config"]["auto_start"] = aux1_auto_start
    if aux2_auto_start is not None:
        config["auxiliaries"]["aux2"]["config"]["auto_start"] = aux2_auto_start

    expected_provide_connector_calls = [
        mocker.call(
            "channel1",
            "channel_module:SomeCChannel",
            **config["connectors"]["channel1"]["config"],
        ),
        mocker.call("proxy_channel_aux1", f"{cc_class.__module__}:{cc_class.__name__}"),
        mocker.call("proxy_channel_aux2", f"{cc_class.__module__}:{cc_class.__name__}"),
    ]

    # auto_start is expected to be set if any of the attached auxiliaries has it explicitly set
    # or if it isn't specified (default is auto_start enabled)
    expected_proxy_auto_start = aux1_auto_start in (True, None) or aux2_auto_start in (
        True,
        None,
    )

    # expected additional kwargs for the provide_auxiliary calls
    expected_aux1_params = {"aux_param1": 1}
    if aux1_auto_start is not None:
        expected_aux1_params.update({"auto_start": aux1_auto_start})
    expected_aux2_params = {"aux_param2": 2}
    if aux2_auto_start is not None:
        expected_aux2_params.update({"auto_start": aux2_auto_start})

    expected_provide_auxiliary_calls = [
        mocker.call(
            "aux1",
            "some_module:Auxiliary",
            aux_cons={"com": "proxy_channel_aux1"},
            **expected_aux1_params,
        ),
        mocker.call(
            "aux2",
            "some_other_module:SomeOtherAuxiliary",
            aux_cons={"com": "proxy_channel_aux2"},
            **expected_aux2_params,
        ),
        mocker.call(
            "proxy_aux_channel1",
            f"{aux_class.__module__}:{aux_class.__name__}",
            aux_cons={"com": "channel1"},
            aux_list=["aux1", "aux2"],
            auto_start=expected_proxy_auto_start,
        ),
    ]

    return config, expected_provide_connector_calls, expected_provide_auxiliary_calls


@pytest.mark.parametrize(
    "sample_config",
    # execute sample_config fixture with the parameters
    # multiprocessing_enabled, aux1_auto_start, aux2_auto_start
    [
        (True, True, True),
        (False, True, True),
        (False, False, True),
        (False, False, False),
        (False, None, False),
        (False, None, None),
    ],
    indirect=True,
    ids=[
        "multiprocessing - auto start",
        "threading - auto start",
        "threading - no auto start aux1",
        "threading - no auto start all auxes",
        "threading - default auto start aux1",
        "threading - default auto start all auxes",
    ],
)
def test_config_registry_auto_proxy(mocker: MockerFixture, sample_config):
    mock_linker = mocker.MagicMock()
    mocker.patch(
        "pykiso.test_setup.config_registry.DynamicImportLinker",
        return_value=mock_linker,
    )

    config, provide_connector_calls, provide_auxiliary_calls = sample_config

    ConfigRegistry.register_aux_con(config)

    mock_linker.install.assert_called_once()
    mock_linker.provide_connector.assert_has_calls(provide_connector_calls, any_order=True)
    mock_linker.provide_auxiliary.assert_has_calls(provide_auxiliary_calls, any_order=True)
    mock_linker._aux_cache.get_instance.assert_called_once_with("proxy_aux_channel1")


def test_config_registry_auto_proxy_creation_error(mocker: MockerFixture, sample_config):
    mock_linker = mocker.MagicMock()
    mocker.patch(
        "pykiso.test_setup.config_registry.DynamicImportLinker",
        return_value=mock_linker,
    )
    mock_delete_aux_con = mocker.patch.object(ConfigRegistry, "delete_aux_con")
    mocker.patch.object(
        ConfigRegistry,
        "get_aux_by_alias",
        side_effect=pykiso.exceptions.AuxiliaryCreationError("proxy_aux_channel1"),
    )

    config, provide_connector_calls, provide_auxiliary_calls = sample_config

    with pytest.raises(pykiso.exceptions.AuxiliaryCreationError):
        ConfigRegistry.register_aux_con(config)

    mock_linker.install.assert_called_once()
    mock_linker.provide_connector.assert_has_calls(provide_connector_calls, any_order=True)
    mock_linker.provide_auxiliary.assert_has_calls(provide_auxiliary_calls, any_order=True)
    mock_delete_aux_con.assert_called_once()


def test_config_registry_no_auto_proxy(mocker: MockerFixture, sample_config):
    mock_make_px_channel = mocker.patch.object(ConfigRegistry, "_make_proxy_channel_config")
    mock_make_px_aux = mocker.patch.object(ConfigRegistry, "_make_proxy_aux_config")
    mock_linker = mocker.MagicMock()
    mocker.patch(
        "pykiso.test_setup.config_registry.DynamicImportLinker",
        return_value=mock_linker,
    )

    config, *_ = sample_config
    config["auxiliaries"]["aux2"]["connectors"]["com"] = "other_channel"

    ConfigRegistry.register_aux_con(config)

    mock_make_px_channel.assert_not_called()
    mock_make_px_aux.assert_not_called()

    mock_linker.install.assert_called_once()
    assert mock_linker.provide_connector.call_count == 1
    assert mock_linker.provide_auxiliary.call_count == 2
    mock_linker._aux_cache.get_instance.assert_not_called()


def test_abort(mocker: MockerFixture, caplog):
    reason = "reason"
    os_kill_mock = mocker.patch("os.kill")

    test_execution.abort(reason)

    assert reason in caplog.text
    assert "Non recoverable error occurred during test execution, aborting test session." in caplog.text
    os_kill_mock.assert_called_once()


@pytest.mark.parametrize(
    "config,expected_strategy",
    [
        (
            {
                "connectors": {"dummychannel": {"type": "dummyType"}},
            },
            False,
        ),
        (
            {
                "connectors": {"dummychannel": {"type": "pykiso.lib.connectors.cc_pcan_can:CCPCanCan"}},
            },
            False,
        ),
        (
            {
                "connectors": {
                    "dummychannel": {
                        "type": "pykiso.lib.connectors.cc_pcan_can:CCPCanCan",
                        "config": {"strategy_trc_file": "testRun"},
                    }
                },
            },
            True,
        ),
    ],
)
def test__check_trace_file_strategy(config, expected_strategy: bool):
    strategy = test_execution._check_trace_file_strategy(config)
    assert expected_strategy is strategy


def test__check_trace_file_strategy_error_raised():
    with pytest.raises(ValueError):
        test_execution._check_trace_file_strategy(
            {
                "connectors": {
                    "dummychannel": {
                        "type": "pykiso.lib.connectors.cc_pcan_can:CCPCanCan",
                        "config": {"strategy_trc_file": "InvalidStrategy"},
                    }
                },
            }
        )


def test__get_connector_instance_with_trace_file_strategy_no_instance_available(mocker: MockerFixture):
    auxiliaries = mocker.MagicMock(spec=DUTAuxiliary)
    auxiliaries.channel = None
    channel_name = "aux"

    pykiso.auxiliaries = mocker.MagicMock()
    mocker.patch.object(pykiso.auxiliaries, channel_name, return_value=auxiliaries)

    instance = test_execution._get_connector_instance_with_trace_file_strategy({"auxiliaries": {channel_name: None}})

    assert instance == None


@pytest.mark.parametrize("channel_class", (CCPCanCan, CCSocketCan))
def test__get_connector_instance_with_trace_file_strategy(
    mocker: MockerFixture, channel_class: CCPCanCan | CCSocketCan
):
    auxiliary = DUTAuxiliary()
    auxiliary.channel = channel_class(strategy_trc_file="testCase")
    aux_name = "aux"

    pykiso.auxiliaries = mocker.Mock()
    pykiso.auxiliaries.aux = auxiliary

    instance = test_execution._get_connector_instance_with_trace_file_strategy({"auxiliaries": {aux_name: None}})

    assert instance == auxiliary.channel


@pytest.mark.parametrize("channel_class", (CCPCanCan, CCSocketCan))
def test__get_connector_instance_with_trace_file_strategy_cc_proxy(
    mocker: MockerFixture, channel_class: CCPCanCan | CCSocketCan
):
    auxiliary = DUTAuxiliary()
    auxiliary.channel = CCProxy()
    auxiliary.channel._proxy = mocker.Mock()
    auxiliary.channel._proxy.channel = channel_class(strategy_trc_file="testCase")
    aux_name = "aux"

    pykiso.auxiliaries = mocker.mock_module.Mock()
    pykiso.auxiliaries.aux = auxiliary

    instance = test_execution._get_connector_instance_with_trace_file_strategy({"auxiliaries": {aux_name: None}})

    assert instance == auxiliary.channel._proxy.channel


@pytest.mark.parametrize("trc_file_strategy", ("testRun", None))
def test_handle_can_trace_strategy_no_change(mocker: MockerFixture, trc_file_strategy):
    mocked_test_suite = [mocker.MagicMock(spec=unittest.TestSuite)] * 4
    mocker.patch.object(test_execution, "_check_trace_file_strategy", return_value=trc_file_strategy)
    mocker.patch.object(test_execution, "_get_connector_instance_with_trace_file_strategy", return_value=None)

    test_suite_returned = test_execution.handle_can_trace_strategy("config", mocked_test_suite)

    assert mocked_test_suite == test_suite_returned


@pytest.mark.parametrize("trc_file_strategy,nb_call_expected", (["testRun", 4], ["testCase", 1]))
def test_handle_can_trace_strategy(mocker: MockerFixture, trc_file_strategy, nb_call_expected):
    test_suite_mock = mocker.MagicMock(spec=unittest.TestSuite)
    test_case_mock = mocker.MagicMock(spec=unittest.TestCase)
    channel_mock = mocker.MagicMock(spec=CCSocketCan)
    channel_mock.strategy_trc_file = trc_file_strategy
    test_case_mock._testMethodName = "testName"
    test_suite_mock._tests = [test_case_mock]
    mocked_test_suite = [test_suite_mock] * 4
    mocker.patch.object(test_execution, "_check_trace_file_strategy", return_value=trc_file_strategy)
    mocker.patch.object(test_execution, "_get_connector_instance_with_trace_file_strategy", return_value=channel_mock)
    start_can_trace_mock = mocker.patch.object(test_execution, "start_can_trace_decorator")
    stop_can_trace_mock = mocker.patch.object(test_execution, "stop_can_trace_decorator")

    test_execution.handle_can_trace_strategy("config", mocked_test_suite)

    assert start_can_trace_mock.call_count == nb_call_expected
    assert stop_can_trace_mock.call_count == nb_call_expected


@pytest.mark.parametrize(
    "channel_class,expected_function", ([CCPCanCan, "start_pcan_trace"], [CCSocketCan, "start_can_trace"])
)
@pytest.mark.parametrize("opened", (True, False))
def test_start_can_trace_decorator(
    mocker: MockerFixture, opened: bool, channel_class: CCPCanCan | CCSocketCan, expected_function: str
):
    pcan_mock = mocker.MagicMock(spec=channel_class)
    pcan_mock.__class__ == channel_class
    pcan_mock.opened = opened
    pcan_mock.trace_path = Path(".")
    trace_name = "file_name"

    def dummy_function():
        return "value"

    dummy_function = test_execution.start_can_trace_decorator(dummy_function, pcan_mock, trace_name)

    returned_value = dummy_function()

    assert returned_value == "value"
    getattr(pcan_mock, expected_function).assert_called_once_with(trace_path=pcan_mock.trace_path / trace_name)
    if not opened:
        pcan_mock.open.assert_called_once()
    else:
        pcan_mock.open.assert_not_called()


@pytest.mark.parametrize(
    "channel_class,expected_function", ([CCPCanCan, "stop_pcan_trace"], [CCSocketCan, "stop_can_trace"])
)
def test_stop_can_trace_decorator(
    mocker: MockerFixture, channel_class: CCPCanCan | CCSocketCan, expected_function: str
):
    pcan_mock = mocker.MagicMock(spec=channel_class)

    def dummy_function():
        return "value"

    dummy_function = test_execution.stop_can_trace_decorator(dummy_function, pcan_mock)

    returned_value = dummy_function()

    assert returned_value == "value"
    getattr(pcan_mock, expected_function).assert_called_once_with()
