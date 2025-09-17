import getpass
import json
from pathlib import Path

import click

from .xray import XrayInterface, extract_test_results


@click.group()
@click.option(
    "-u",
    "--user",
    help="Xray user id",
    required=True,
    default=None,
    hide_input=True,
)
@click.option(
    "-p",
    "--password",
    help="Valid Xray API key (if not given ask at command prompt level)",
    required=False,
    default=None,
    hide_input=True,
)
@click.option(
    "--url",
    help="Base URL of Xray server",
    required=True,
)
@click.pass_context
def cli_xray(ctx: dict, user: str, password: str, url: str) -> None:
    """Xray interaction tool."""
    ctx.ensure_object(dict)
    ctx.obj["USER"] = user or input("Enter Client ID Xray and Press enter:")
    ctx.obj["PASSWORD"] = password or getpass.getpass("Enter your password and Press ENTER:")
    ctx.obj["URL"] = url


@cli_xray.command("upload")
@click.option(
    "--test-execution-key",
    help="Key of the test execution ticket where to overwrite the test results from a JUnit xml",
    required=False,
    default=None,
    type=click.STRING,
)
@click.option(
    "-r",
    "--path-results",
    help="Full path to a JUnit report or to the folder containing the JUNIT reports",
    type=click.Path(exists=True, resolve_path=True),
    required=True,
)
@click.option(
    "-i",
    "--test-execution-description",
    help="Update the description of the test execution ticket created",
    required=False,
    default=None,
    type=click.STRING,
)
@click.option(
    "-n",
    "--test-execution-summary",
    help="Update the summary of the test execution ticket created",
    required=False,
    default=None,
    type=click.STRING,
)
@click.option(
    "--test-plan-key",
    help="Key of the test plan ticket where to add new test execution for the test results from a JUnit xml",
    required=False,
    default=None,
    type=click.STRING,
)
@click.option(
    "-m",
    "--merge-xml-files",
    help="Merge multiple xml files to be send in one xml file",
    is_flag=True,
    required=False,
)
@click.option(
    "-na",
    "--not-append-test-results",
    help="Do not append new test keys from the .xml(s) to the updated test execution, only overwrite already existing ones",
    is_flag=True,
    default=False,
    required=False,
)
@click.pass_context
def cli_upload(
    ctx,
    path_results: str,
    test_execution_key: str,
    test_execution_description: str,
    test_execution_summary: str,
    test_plan_key: str,
    merge_xml_files: bool,
    not_append_test_results: bool,
) -> None:
    """Upload the JUnit xml test results on xray.

    :param ctx: click context
    :param path_results: path to the junit xml files containing the test result reports
    :param test_execution_key: test execution key where to upload the test results
    :param test_execution_description: update the test execution ticket description - otherwise, keep current description
    :param test_execution_summary: update the test execution ticket summary - otherwise, keep current summary
    :param test_plan_key: test plan key where to create a new test execution ticket for the test results
    :param merge_xml_files: if True, merge the xml files, else do nothing
    :param not_append_test_results: if True, only overwrite the existing ones (update only), else append the new results from the .xml file(s) to the test execution

    """
    if test_plan_key and test_execution_key:
        raise ValueError(
            "You cannot specify both a test plan key and a test execution key. " "Please use either one or the other."
        )
    # If a new test execution ticket is being created (no key), the user should pass a description and a summary.
    if not test_execution_key and (not test_execution_description or not test_execution_summary):
        raise ValueError(
            "Creating a new test execution ticket requires both a description and a summary in the CLI options"
        )

    # Create XrayInterface once for authentication optimization
    xray_interface = XrayInterface(
        base_url=ctx.obj["URL"], client_id=ctx.obj["USER"], client_secret=ctx.obj["PASSWORD"]
    )

    # If the user chooses not to append new test results to an existing test execution ticket,
    # retrieve the existing test keys from Jira for the specified test execution ticket.
    # If appending is allowed, there is no need to fetch the existing test keys.
    if not_append_test_results and test_execution_key:
        print("Preparing the ticket for update...")
        jira_keys = xray_interface.get_jira_test_keys_from_test_execution_ticket(test_execution_key)
    else:
        jira_keys = []

    # From the JUnit xml files found, create a list of the dictionary per test results marked with an xray decorator.
    path_results = Path(path_results).resolve()
    test_results = extract_test_results(
        path_results=path_results,
        merge_xml_files=merge_xml_files,
        jira_keys=jira_keys,
        test_execution_key=test_execution_key,
        test_execution_summary=test_execution_summary,
        test_execution_description=test_execution_description,
        test_plan_key=test_plan_key,
    )

    responses = []
    for result in test_results:
        # Upload the test results into Xray using the same interface instance
        responses.append(xray_interface.upload_test_results(data=result))
    responses_result_str = json.dumps(responses, indent=2)
    print(f"The test results can be found in JIRA by: {responses_result_str}")
