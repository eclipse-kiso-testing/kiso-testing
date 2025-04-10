import getpass
import json
from pathlib import Path

import click

from .xray import extract_test_results_from_junit, extract_test_results_from_pickle, upload_test_results
from .xray_report import create_result_dictionary, merge_results


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
    "--test-execution-id",
    help="Import the JUnit xml test results into an existing Test Execution ticket by overwriting",
    required=False,
    default=None,
    type=click.STRING,
)
@click.option(
    "--path-results-junit",
    help="Full path to a JUnit report or to the folder containing the test results reports",
    type=click.Path(exists=True, resolve_path=True),
    required=False,
)
@click.option(
    "--path-results-pickle",
    help="Full path to a JUnit report or to the folder containing the test results reports",
    type=click.Path(exists=True, resolve_path=True),
    required=False,
)
@click.option(  # TODO: to keep or to delete
    "-k",
    "--project-key",
    help="Key of the project",
    type=click.STRING,
    required=False,
)
@click.option(  # TODO: to keep or to delete
    "-n",
    "--test-execution-name",
    help="Name of the test execution ticket created",
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
@click.option(  # TODO: to keep or to delete
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
    test_execution_id: str,
    project_key: str,
    test_execution_name: str,
    merge_xml_files: bool,
    import_description: bool,
    path_results_junit: str | None = None,
    path_results_pickle: str | None = None,
) -> None:
    """Upload the JUnit xml test results or pickle test results on xray.

    :param ctx: click context
    :param test_execution_id: test execution ID where to upload the test results
    :param project_key: project key ID of the xray ticket to link the created test execution ticket
    :param test_execution_name: name of the test execution ticket
    :param merge_xml_files: if True, merge the xml files, else do nothing
    :param import_description: if True, change the ticket description with the test function description
    :param path_results_junit: path to the junit xml files containing the test result reports
    :param path_results_pickle: path to the pickle files containing the test result reports
    """
    if path_results_junit is None and path_results_pickle is None:
        raise ValueError(
            "Please provide a path to the JUnit xml test results or pickle test results or to the folder containing them."
        )

    # From the JUnit xml files found, create a temporary file to keep only the test results marked with an xray decorator.
    if path_results_junit is not None:
        path_results = Path(path_results_junit).resolve()
        test_results = extract_test_results_from_junit(
            path_results=path_results, merge_xml_files=merge_xml_files, update_description=import_description
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
                    # test_execution_id=test_execution_id,
                    # project_key=project_key,
                    # test_execution_name=test_execution_name,
                )
            )
        responses_result_str = json.dumps(responses, indent=2)
        print(f"The test results can be found in JIRA by: {responses_result_str}")

    # From the pickle files found, create a dictionary to keep only the required test results
    if path_results_pickle is not None:
        path_results = Path(path_results_pickle).resolve()
        test_results = extract_test_results_from_pickle(path_results=path_results)

        # parse info to be send to xray
        print("Generating dictionary of the test results to be sent to Xray...")
        for result in test_results:
            xray_results = create_result_dictionary(result, test_execution_id)
            xray_results = merge_results(xray_results)
            # upload to xray
            responses = []
            for xray_result in xray_results:
                responses.append(
                    upload_test_results(
                        base_url=ctx.obj["URL"],
                        user=ctx.obj["USER"],
                        password=ctx.obj["PASSWORD"],
                        results=xray_result,
                    )
                )
            responses_result_str = json.dumps(responses, indent=2)
            print(f"The test results can be found in JIRA by: {responses_result_str}")
