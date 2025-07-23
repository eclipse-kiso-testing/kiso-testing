import json
import tempfile
from pathlib import Path

import requests
import xmltodict
from junitparser.cli import merge as merge_junit_xml
from requests.auth import AuthBase

from ...tool.xray.xray_report import create_result_dictionary, reformat_xml_results

API_VERSION = "api/v2/"
AUTHENTICATE_ENDPOINT = "/api/v2/authenticate"


class XrayException(Exception):
    """Raise when sending the post request is unsuccessful."""

    def __init__(self, message=""):
        self.message = message


class ClientSecretAuth(AuthBase):
    """Bearer authentication with Client ID and a Client Secret."""

    def __init__(self, base_url: str, client_id: str, client_secret: str, verify: bool | str = True) -> None:
        if base_url.endswith("/"):
            base_url = base_url[:-1]
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.verify = verify

    @property
    def endpoint_url(self) -> str:
        """Return full URL to the authenticate server."""
        return f"{self.base_url}{AUTHENTICATE_ENDPOINT}"

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        headers = {"Content-type": "application/json", "Accept": "text/plain"}
        auth_data = {"client_id": self.client_id, "client_secret": self.client_secret}

        try:
            response = requests.post(self.endpoint_url, data=json.dumps(auth_data), headers=headers, verify=self.verify)
        except requests.exceptions.ConnectionError as exc:
            err_message = f"ConnectionError: cannot authenticate with {self.endpoint_url}"
            raise XrayException(err_message) from exc
        else:
            auth_token = response.text.replace('"', "")
            r.headers["Authorization"] = f"Bearer {auth_token}"
        return r


class XrayPublisher:
    """Xray Publisher command API."""

    def __init__(self, base_url: str, endpoint: str, auth: ClientSecretAuth, verify: bool | str = True) -> None:
        self.base_url = base_url[:-1] if base_url.endswith("/") else base_url
        self.endpoint = endpoint
        self.rest_api_version = API_VERSION
        self.auth = auth
        self.verify = verify

    @property
    def endpoint_url(self) -> str:
        """Return full URL complete url to send the post request.to the xray server."""
        return self.base_url + self.endpoint

    def publish_xml_result(self, data: dict) -> dict[str, str]:
        """
        Publish the xml test results to xray.

        :param data: the test results

        :return: the content of the post request to create the execution test ticket: its id, its key, and its issue
        """
        print("Uploading test results to Xray...")
        # construct the request header
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        try:
            query_response = requests.request(
                method="POST", url=self.endpoint, headers=headers, json=data, auth=self.auth, verify=self.verify
            )
        except requests.exceptions.ConnectionError:
            raise XrayException(f"Cannot connect to JIRA service at {self.endpoint}")
        else:
            query_response.raise_for_status()

        return json.loads(query_response.content)

    def get_internal_id_from_key(self, jira_key: str) -> str:
        """
        Convert the Jira key to the internal issueId

        :param jira_key: the jira key of the test execution (e.g ABC-123)

        :return: the corresponding internal xray issue id
        """
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.auth}"}

        # GraphQL query
        query = (
            """
        query {
            getTestExecutions(jql: "key='%s'", limit: 1) {
                results {
                    issueId
                }
            }
        }
        """
            % jira_key
        )

        payload = {"query": query}

        try:
            query_response = requests.request(
                method="POST", url=self.endpoint, headers=headers, json=payload, auth=self.auth, verify=self.verify
            )

            data = query_response.json()

            if (
                "data" in data
                and "getTestExecutions" in data["data"]
                and "results" in data["data"]["getTestExecutions"]
                and len(data["data"]["getTestExecutions"]["results"]) > 0
            ):
                issue_id = data["data"]["getTestExecutions"]["results"][0]["issueId"]
                return issue_id

        except requests.exceptions.ConnectionError:
            raise XrayException(f"Cannot connect to JIRA service at {self.endpoint}")
        else:
            query_response.raise_for_status()
            return None

    def get_test_execution_results(self, test_execution_id: str) -> list[str]:
        """
        Get the tests' issue ids inside the given test execution id

        :param test_execution_id: the test execution id

        :return: the list of issue ids inside the test execution results
        """

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.auth}"}

        # GraphQL query
        query = (
            """
        query {
            getTestExecution(issueId: "%s") {
                issueId
                tests(limit: 100) {
                    total
                    start
                    limit
                    results {
                        issueId
                        testType {
                            name
                        }
                    }
                }
            }
        }
        """
            % test_execution_id
        )

        payload = {"query": query}
        try:
            query_response = requests.request(
                method="POST", url=self.endpoint, headers=headers, json=payload, auth=self.auth, verify=self.verify
            )

            data = query_response.json()

            # Extract issueIds from results
            if (
                "data" in data
                and "getTestExecution" in data["data"]
                and "tests" in data["data"]["getTestExecution"]
                and "results" in data["data"]["getTestExecution"]["tests"]
            ):
                results = data["data"]["getTestExecution"]["tests"]["results"]
                issue_ids = [result["issueId"] for result in results]
                return issue_ids

        except requests.exceptions.ConnectionError:
            raise XrayException(f"Cannot connect to JIRA service at {self.endpoint}")

        else:
            query_response.raise_for_status()

        return []

    def get_jira_keys_for_tests(self, issue_ids: list[str]) -> list[str]:
        """
        Get Jira keys for each test

        :param issue_ids: list of xray issue ids

        :return: the jira keys corresponding to the issue ids
        """

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.auth}"}

        jira_keys = []

        for issue_id in issue_ids:
            query = (
                """
            query {
                getTest(issueId: "%s") {
                    jira(fields: ["key", "summary"])
                    testType {
                        name
                    }
                }
            }
            """
                % issue_id
            )

            payload = {"query": query}

            try:
                query_response = requests.request(
                    method="POST", url=self.endpoint, headers=headers, json=payload, auth=self.auth, verify=self.verify
                )

                data = query_response.json()

                if (
                    "data" in data
                    and "getTest" in data["data"]
                    and data["data"]["getTest"]
                    and "jira" in data["data"]["getTest"]
                ):
                    jira_key = data["data"]["getTest"]["jira"]["key"]
                    jira_keys.append(jira_key)

            except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError) as e:  # noqa F841
                continue

        return jira_keys

    def get_all_test_jira_keys(self, test_execution_id: str) -> list[str]:
        """
        Get all Jira keys for tests in a test execution

        :param test_execution_id: the test execution id (e.g ABC-1234)

        :return: the list of jira keys inside the test execution results
        """

        # Convert the provided jira key to the internal issue id
        xray_id = self.get_internal_id_from_key(test_execution_id)
        # Get all issue IDs from the test execution
        issue_ids = self.get_test_execution_results(xray_id)

        if not issue_ids:
            return []

        # Get all Jira keys for these issues
        jira_keys = self.get_jira_keys_for_tests(issue_ids)

        return jira_keys


def upload_test_results(
    base_url: str,
    user: str,
    password: str,
    results: str,
) -> dict[str, str]:
    """
    Upload all given results to xray.

    :param base_url: the xray's base url
    :param user: the user's session id
    :param password: the user's password
    :param results: the test results

    :return: the content of the post request to create the execution test ticket: its id, its key, and its issue
    """
    endpoint_url = "https://xray.cloud.getxray.app/api/v2/import/execution"
    # authenticate: get the correct token from the authenticate endpoint
    client_secret_auth = ClientSecretAuth(base_url=base_url, client_id=user, client_secret=password, verify=True)
    xray_publisher = XrayPublisher(base_url=base_url, endpoint=endpoint_url, auth=client_secret_auth)

    # publish: post request to send the test results to xray endpoint
    responses = xray_publisher.publish_xml_result(data=results)
    return responses


def get_test_execution_jira_test_keys(
    base_url: str,
    user: str,
    password: str,
    test_execution_id: str,
) -> list[str]:
    """
    Upload all given results to xray.

    :param base_url: the xray's base url
    :param user: the user's session id
    :param password: the user's password
    :param results: the test results

    :return: the content of the post request to create the execution test ticket: its id, its key, and its issue
    """

    graphql_url = "https://xray.cloud.getxray.app/api/v2/graphql"
    # authenticate: get the correct token from the authenticate endpoint
    client_secret_auth = ClientSecretAuth(base_url=base_url, client_id=user, client_secret=password, verify=True)
    xray_publisher = XrayPublisher(base_url=base_url, endpoint=graphql_url, auth=client_secret_auth)

    # publish: post request to send the test results to xray endpoint
    jira_keys = xray_publisher.get_all_test_jira_keys(test_execution_id)
    return jira_keys


def extract_test_results(
    ctx,
    path_results: Path,
    merge_xml_files: bool,
    not_append_test_results: bool,
    test_execution_key: str | None = None,
    test_execution_summary: str | None = None,
    test_execution_description: str | None = None,
) -> list[str]:
    """
    Extract the test results linked to an xray test key. Filter the JUnit xml files generated by the execution of tests,
    to keep only the results of tests marked with an xray decorator. A temporary file is created with the test results.

    :param ctx: click context
    :param path_results: the path to the xml files
    :param merge_xml_files: merge all the files to return only a list with one element
    :param not_append_test_results: if True, only overwrite the existing ones (update only), else append the new results from the .xml file(s) to the test execution
    :param test_execution_key: the xray's test execution ticket key where to import the test results,
        if none is specified a new test execution ticket will be created
    :param test_execution_summary: update the test execution ticket summary - otherwise, keep current summary
    :param test_execution_description: update the test execution ticket description - otherwise, keep current description

    :return: the filtered test results"""
    xml_results = []
    if path_results.is_file():
        if path_results.suffix != ".xml":
            raise RuntimeError(
                f"Expected xml file but found a {path_results.suffix} file instead, from path {path_results}"
            )
        file_to_parse = [path_results]
    elif path_results.is_dir():
        file_to_parse = list(path_results.glob("*.xml"))
        if not file_to_parse:
            raise RuntimeError(f"No xml found in following repository {path_results}")

    with tempfile.TemporaryDirectory() as xml_dir:
        if merge_xml_files and len(file_to_parse) > 1:
            xml_dir = Path(xml_dir).resolve()
            xml_path = xml_dir / "xml_merged.xml"
            merge_junit_xml(file_to_parse, xml_path, None)
            file_to_parse = [xml_path]

        # use xml to json
        for file in file_to_parse:
            with open(file) as xml_file:
                data_dict = xmltodict.parse(xml_file.read(), attr_prefix="")

            # get the test execution test results keys in case of overwrite only
            if test_execution_key and not_append_test_results:
                print("Preparing the ticket for update...")
                jira_keys = get_test_execution_jira_test_keys(
                    ctx.obj["URL"], ctx.obj["USER"], ctx.obj["PASSWORD"], test_execution_key
                )
            else:
                jira_keys = []

            xray_dict = create_result_dictionary(
                data_dict["testsuites"]["testsuite"], jira_keys, test_execution_summary, test_execution_description
            )
            xml_results = reformat_xml_results(xray_dict, test_execution_key)
        return xml_results
