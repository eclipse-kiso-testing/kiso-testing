##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

import click
import pytest
from click.testing import CliRunner

from pykiso import cli


@pytest.fixture()
def runner():
    return CliRunner()


def test_main(runner):
    runner.invoke(
        cli.main,
        [
            "pykiso",
            "-c",
            "examples/acroname.yaml",
            "-c",
            "examples/acroname.yaml",
        ],
    )


@pytest.mark.parametrize(
    "user_tags,expected_results",
    [
        (["--branch-level", "dev"], {"branch-level": ["dev"]}),
        (["--branch-level", "dev,master"], {"branch-level": ["dev", "master"]}),
        (
            ["--branch-level", "dev", "--variant", "delta"],
            {"branch-level": ["dev"], "variant": ["delta"]},
        ),
    ],
)
def test_eval_user_tags(user_tags, expected_results, mocker):
    click_context_mock = mocker.MagicMock()
    click_context_mock.args = user_tags
    user_tags = cli.eval_user_tags(click_context_mock)
    assert user_tags == expected_results


def test_eval_user_tags_empty(mocker):
    click_context_mock = mocker.MagicMock()
    click_context_mock.args = []
    user_tags = cli.eval_user_tags(click_context_mock)
    assert user_tags == {}


@pytest.mark.parametrize(
    "user_tags,expected_message",
    [
        (
            ["branch-level", "dev"],
            " branch-level",
        ),
        (
            ["--forbidden_underscore", "dev"],
            "--forbidden_underscore",
        ),
    ],
)
def test_eval_user_tags_exception_no_such_option(user_tags, expected_message, mocker):
    # user_tags = ["branch-level", "dev"]
    click_context_mock = mocker.MagicMock()
    click_context_mock.args = user_tags
    with pytest.raises(click.NoSuchOption) as exec_info:
        eval_user_tags = cli.eval_user_tags(click_context_mock)
    assert expected_message in exec_info.value.format_message()


def test_eval_user_tags_exception_bad_option_usage(mocker):
    click_context_mock = mocker.MagicMock()
    click_context_mock.args = ["--branch-level"]
    with pytest.raises(click.BadOptionUsage) as exec_info:
        eval_user_tags = cli.eval_user_tags(click_context_mock)
    assert "tag --branch-level" in exec_info.value.format_message()


def test_check_file_extension_bad_param(mocker):
    click_context_mock = mocker.MagicMock()
    click_param_mock = mocker.MagicMock()
    not_yaml_file = "./fail.txt"
    paths = ("./success.yaml", not_yaml_file)
    with pytest.raises(click.BadParameter) as exec_info:
        cli.check_file_extension(click_context_mock, click_param_mock, paths)
    assert not_yaml_file in exec_info.value.format_message()
    assert "needs to be a .yaml file" in exec_info.value.format_message()


def test_check_file_extension(mocker):
    click_context_mock = mocker.MagicMock()
    click_param_mock = mocker.MagicMock()
    paths = ("./complete/success.yaml", "./success.yml")
    actual = cli.check_file_extension(click_context_mock, click_param_mock, paths)
    assert actual == paths


def test_check_and_handle_unresolved_threads_no_unresolved_threads(mocker):
    log_mock = mocker.MagicMock()
    mocker.patch("pykiso.cli.active_threads", return_value=[])
    cli.check_and_handle_unresolved_threads(log_mock, 0)
    log_mock.warning.assert_not_called()
    log_mock.fatal.assert_not_called()


def test_check_and_handle_unresolved_threads_with_unresolved_threads_resolved_before_timeout(mocker):
    log_mock = mocker.MagicMock()
    mocker.patch("pykiso.cli.active_threads", side_effect=[[("Thread-1", "Thread-1 frame")], []])
    mocker.patch("time.sleep", return_value=None)
    cli.check_and_handle_unresolved_threads(log_mock, 0, timeout=5)
    log_mock.warning.assert_called()
    log_mock.fatal.assert_not_called()


def test_check_and_handle_unresolved_threads_with_unresolved_threads_not_resolved_after_timeout(mocker):
    log_mock = mocker.MagicMock()
    mocker.patch("pykiso.cli.active_threads", return_value=[("Thread-1", "Thread-1 frame")])
    mocker.patch("threading.active_count", return_value=2)
    mocker.patch("time.sleep", return_value=None)
    os_mock = mocker.patch("os._exit", return_value=None)
    cli.check_and_handle_unresolved_threads(log_mock, 0, timeout=5)
    log_mock.warning.assert_called()
    log_mock.fatal.assert_called()
    os_mock.assert_called_with(0)


def test_active_threads(mocker):
    """Get the names of all active threads except the main thread."""
    main_thread = mocker.MagicMock()
    main_thread.configure_mock(name="Thread-Main")

    other_thread = mocker.MagicMock()
    other_thread.configure_mock(name="Thread-1")

    mocker.patch("threading.enumerate", return_value=[main_thread, other_thread])
    actual = [thread[0] for thread in cli.active_threads()]
    assert actual == ["Thread-1"]
