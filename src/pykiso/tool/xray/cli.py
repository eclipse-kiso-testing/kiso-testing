import getpass
import json
from pathlib import Path

import click

from .xray import extract_test_results, upload_test_results


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
    "-n",
    "--test-execution-summary",
    help="Summary of the test execution ticket created",
    type=click.STRING,
    required=False,
)
@click.option(
    "-m",
    "--merge-xml-files",
    help="Merge multiple xml files to be send in one xml file",
    is_flag=True,
    required=False,
)
@click.option(
    "-i",
    "--import-description",
    help="Import the test function description as the xray ticket description",
    is_flag=True,
    required=False,
    default=True,
)
@click.pass_context
def cli_upload(
    ctx,
    path_results: str,
    test_execution_key: str,
    test_execution_summary: str,
    merge_xml_files: bool,
    import_description: bool,
) -> None:
    """Upload the JUnit xml test results on xray.

    :param ctx: click context
    :param path_results: path to the junit xml files containing the test result reports
    :param test_execution_key: test execution key where to upload the test results
    :param test_execution_summary: summary of the test execution ticket
    :param merge_xml_files: if True, merge the xml files, else do nothing
    :param import_description: if True, change the ticket description with the test function description
    """
    # From the JUnit xml files found, create a list of the dictionary per test results marked with an xray decorator.
    path_results = Path(path_results).resolve()
    test_results = extract_test_results(
        path_results=path_results,
        merge_xml_files=merge_xml_files,
        update_description=import_description,
        test_execution_key=test_execution_key,
        test_execution_summary=test_execution_summary,
    )

    responses = []
    for result in test_results:
        # Upload the test results into Xray
        responses.append(
            upload_test_results(
                base_url=ctx.obj["URL"],
                user=ctx.obj["USER"],
                password=ctx.obj["PASSWORD"],
                results=result,
            )
        )
    responses_result_str = json.dumps(responses, indent=2)
    print(f"The test results can be found in JIRA by: {responses_result_str}")
