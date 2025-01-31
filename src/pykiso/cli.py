##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Integration Test Framework
**************************

:module: cli

:synopsis: Entry point to the integration test framework.

.. currentmodule:: cli

"""
import logging
import os
import pprint
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click

import pykiso.profiling  # noqa: needs to be imported to trace from the beginning

from . import __version__
from .config_parser import parse_config
from .global_config import Grabber
from .logging_initializer import change_logger_class, initialize_logging
from .test_coordinator import test_execution
from .test_setup.config_registry import ConfigRegistry
from .types import PathType

UNRESOLVED_THREAD_TIMEOUT = 10


def eval_user_tags(click_context: click.Context) -> Dict[str, List[str]]:
    """Evaluate commandline args for user tags and raise exceptions for invalid
    arguments.

    :param click_context: click context
    :raises click.NoSuchOption: if key doesn't start with "--" or has an invalid
      character like "_"
    :raises click.BadOptionUsage: no value specified for user tag
    :return: user tags with values
    """
    user_tags = {}
    user_args = click_context.args.copy()
    if not user_args:
        return user_tags
    while user_args:
        try:
            key = user_args.pop(0)
            if not key.startswith("--") or "_" in key:
                correct_key = f'{"" if key.startswith("--") else "--"}{key.replace("_", "-")}'
                raise click.NoSuchOption(option_name=key, possibilities=[correct_key])

            value = user_args.pop(0)
            user_tags[key[2:]] = value.split(",")
        except IndexError:
            raise click.BadOptionUsage(
                option_name=key,
                message=f"No value specified for tag {key}",
                ctx=click_context,
            )
    return user_tags


def check_file_extension(click_context: click.Context, param: click.Parameter, paths: Tuple[str]) -> Tuple[str]:
    """Check the path strings of all given test configuration files for yaml file
    extension and raise an exception if the check fails

    :click_context: click context (click callback requirement)
    :param: click parameter (click callback requirement)
    :paths: the paths of the files to check
    :raises click.BadParameter: if one of the files does not have .yaml or .yml
        as extension
    :return: the checked paths as they were passed
    """
    for path in paths:
        if not path.endswith((".yaml", ".yml")):
            raise click.BadParameter(f"Configuration needs to be a .yaml file, but {path} was given")
    return paths


def active_threads() -> list[tuple[str, str]]:
    """Get the names and current execution frame of all active threads except the main thread.

    :return: The the thread name and the frame of the thread
    """
    frames = sys._current_frames()
    return [(thread.name, str(frames.get(thread.ident))) for thread in threading.enumerate()][1:]


def check_and_handle_unresolved_threads(log: logging.Logger, exit_code: int, timeout: int = 10) -> None:
    """Check if there are unresolved threads and handle them.

    :param log: logger
    :param exit_code: exit code to use if unresolved threads are still running after the timeout
    :param timeout: timeout in seconds to wait for unresolved threads to be terminated

    Process for unresolved threads:
    - If there are unresolved threads, log a warning and wait for a timeout.
    - If the threads are still running after the timeout, log a fatal error and force exit.
    - If the threads are properly shut down, log a warning and exit normally.
    """
    # Skip main thread and get running threads
    running_threads = active_threads()

    if len(running_threads) > 0:
        for thread_name, frame in running_threads:
            log.warning(f"Unresolved thread {thread_name} is still running. Frame: {frame}")
        log.warning(f"Wait {timeout}s for unresolved threads to be terminated.")
        time.sleep(timeout)
        if threading.active_count() > 1:
            log.fatal(
                f"Unresolved threads {', '.join([thread_name for thread_name, _ in active_threads()])} are still running after {timeout} seconds. Force pykiso to Exit."
            )
            os._exit(exit_code)
        else:
            log.warning("Unresolved threads has been properly shut down. Normal exit.")


class CommandWithOptionalFlagValues(click.Command):
    """Custom command that allows specifying flags with a value, e.g. ``pykiso -c config.yaml --junit=./reports``."""

    def parse_args(self, ctx, args):
        """Translate any flag `--junit=value` as flag `--junit` with changed flag_value=value"""
        # filter out flags from all of the command parameters
        flags = [
            flag
            for flag in self.params
            if isinstance(flag, click.Option) and flag.is_flag and not isinstance(flag.flag_value, bool)
        ]
        # iterate over all user provided arguments to match the flags with format '--flag=value'
        for arg_index, arg in enumerate(args):
            arg = arg.split("=")
            if len(arg) != 2:
                continue
            arg_name, arg_value = arg
            for flag in flags:
                # if the argument is a flag with a value, rewrite the argument as a regular flag with the appropriate value
                if arg_name in flag.opts:
                    flag.flag_value = arg_value
                    args[arg_index] = arg_name
                    break

        result_args = super(CommandWithOptionalFlagValues, self).parse_args(ctx, args)
        return result_args


@click.command(
    context_settings={
        "help_option_names": ["-h", "--help"],
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
    cls=CommandWithOptionalFlagValues,
)
@click.option(
    "-c",
    "--test-configuration-file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    multiple=True,
    callback=check_file_extension,
    help="path to the test configuration file (in YAML format)",
)
@click.option(
    "-l",
    "--log-path",
    required=False,
    default=None,
    type=click.Path(writable=True),
    multiple=True,
    help="path to log-file or folder. If not set will log to STDOUT",
)
@click.option(
    "--log-level",
    required=False,
    default="INFO",
    type=click.Choice(
        "DEBUG INFO WARNING ERROR".split(" "),
        case_sensitive=False,
    ),
    help="set the verbosity of the logging",
)
@click.option(
    "--junit",
    is_flag=True,
    flag_value="reports",
    help="Enable junit reports, if you want to save report in specific dir relative to current or .xml file, use --junit=(name or dir). The default dir is './reports' and default name is '%Y-%m-%d_%H-%M-%S-{config_name}.xml'",
)
@click.option(
    "--step-report",
    required=False,
    default=None,
    type=click.Path(writable=True),
    help="generate the step report at the specified path",
)
@click.option(
    "--failfast",
    is_flag=True,
    help="stop the test run on the first error or failure",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    required=False,
    help="activate the internal framework logs",
)
@click.option(
    "-p",
    "--pattern",
    type=click.STRING,
    required=False,
    help="test filter pattern, e.g. 'test_suite_1.py' or 'test_*.py'. Or even more granularly 'test_suite_1.py::TestClass::test_name'",
)
@click.option(
    "--logger",
    type=click.STRING,
    required=False,
    help="use the specified logger class in pykiso",
)
@click.version_option(__version__)
@click.pass_context
@Grabber.grab_cli_config
def main(
    click_context: click.Context,
    test_configuration_file: Tuple[PathType],
    log_path: Tuple[PathType] = None,
    log_level: str = "INFO",
    report_type: str = "text",
    step_report: Optional[PathType] = None,
    pattern: Optional[str] = None,
    failfast: bool = False,
    verbose: bool = False,
    logger: Optional[str] = None,
    junit: Optional[str] = None,
):
    """Embedded Integration Test Framework - CLI Entry Point.

    TAG Filters: any additional option to be passed to the test as tag through
    the pykiso call. Multiple values must be separated with a comma.

    For example: pykiso -c your_config.yaml --branch-level dev,master --variant delta

    \f
    :param click_context: click context
    :param test_configuration_file: path to the YAML config file
    :param log_path: path to existing directories or files to write logs to
    :param log_level: any of DEBUG, INFO, WARNING, ERROR
    :param report_type: if "test", the standard report, if "junit", a junit report is generated
    :param variant: allow the user to execute a subset of tests based on variants
    :param branch_level: allow the user to execute a subset of tests based on branch levels
    :param step_report: file path for the step report or None
    :param pattern: overwrite the pattern from the YAML file for easier test development
    :param failfast: stop the test run on the first error or failure
    :param verbose: activate logging for the whole framework
    :param logger: class of the logger that will be used in the tests
    """
    # we are expecting one log file path or as many as the provided configuration files
    if log_path and len(log_path) not in (1, len(test_configuration_file)):
        raise click.UsageError(
            f"Mismatch: {len(log_path)} log files were provided for {len(test_configuration_file)} yaml configuration files"
        )

    if junit is not None:
        report_type = "junit"

    # parse provided tags (any unknown option)
    user_tags = eval_user_tags(click_context)

    if logger:
        change_logger_class(log_level, verbose, logger)

    for idx, config_file in enumerate(test_configuration_file):
        yaml_name = Path(config_file).stem

        # Setup the logging
        if log_path:
            # Put all logs in one file if only one file is provided, otherwise use a new file for each yaml
            log_file = log_path[0] if len(log_path) == 1 else log_path[idx]
        else:
            log_file = None

        log = initialize_logging(log_file, log_level, verbose, report_type, yaml_name)

        # Get YAML configuration
        cfg_dict = parse_config(config_file)
        log.debug("cfg_dict:\n%s", pprint.pformat(cfg_dict))

        # Run tests
        with ConfigRegistry.provide_auxiliaries(cfg_dict):
            exit_code = test_execution.execute(
                cfg_dict,
                report_type,
                yaml_name,
                user_tags,
                step_report,
                pattern,
                failfast,
                junit,
            )

        for handler in logging.getLogger().handlers:
            if isinstance(handler, logging.FileHandler):
                logging.getLogger().removeHandler(handler)

        check_and_handle_unresolved_threads(log, exit_code=exit_code, timeout=UNRESOLVED_THREAD_TIMEOUT)

    sys.exit(exit_code)
