import json
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

import requests
from junitparser.cli import merge as merge_junit_xml

API_VERSION = "api/v2/"


class XrayException(Exception):
    """Raise when sending the post request is unsuccessful."""


class XrayPublisher:
    """Xray Publisher command API."""

    def __init__(self, base_url: str, client_id: str, client_secret: str) -> None:
        self.base_url = base_url[:-1] if base_url.endswith("/") else base_url
        self.rest_api_version = API_VERSION
        self.client_id = client_id
        self.client_secret = client_secret

    def get_url(self, url_endpoint: str) -> str:
        """
        Get the complete url to send the post request.

        :param url_endpoint: the endpoint of the url

        :return: the complete url to send the post request
        """
        return f"{self.base_url}/{self.rest_api_version}{url_endpoint}"

    def get_token(self, url: str) -> str:
        """
        Get the token to authenticate to xray from a client ID and a client SECRET.

        :param url: the url to send the post request to authenticate
        :raises HTTPError: if the token couldn't be retrieved
        :return: the Bearer token
        """
        client = {"client_id": self.client_id, "client_secret": self.client_secret}
        headers = {"Content-Type": "application/json"}
        token_result = requests.post(url=url, headers=headers, json=client)
        token_result.raise_for_status()
        return token_result.json()

    def get_publisher_headers(self, token: str) -> dict[str, str]:
        """
        Get the request header by adding content and authorization part.

        :param token: the requested Bearer token

        :return: the post request's header
        """
        headers = {"Authorization": "Bearer " + token}
        headers["Content-Type"] = "test/xml"
        return headers

    def publish_xml_result(
        self,
        token: str,
        data: dict,
        project_key: str,
        test_execution_id: str | None = None,
        test_execution_name: str | None = None,
    ) -> dict[str, str]:
        """
        Publish the xml test results to xray.

        :param token: the requested Bearer token
        :param data: the test results
        :param test_execution_id: the xray's test execution ticket id where to import the test results,
            if none is specified a new test execution ticket will be created

        :return: the content of the post request to create the execution test ticket: its id, its key, and its issue
        """
        if test_execution_name is None:
            return self._publish_xml_result(
                token=token, data=data, project_key=project_key, test_execution_id=test_execution_id
            )
        return self._publish_xml_result_multipart(
            token=token,
            data=data,
            project_key=project_key,
            test_execution_name=test_execution_name,
        )

    def _publish_xml_result(
        self, token: str, data: dict, project_key: str, test_execution_id: str | None = None
    ) -> dict[str, str]:
        # construct the request header
        headers = self.get_publisher_headers(token)

        url_endpoint = f"import/execution/junit/?projectKey={project_key}"
        if test_execution_id is not None:
            url_endpoint += f"&testExecKey={test_execution_id}"

        # construct the complete url to send the post request
        url_publisher = self.get_url(url_endpoint=url_endpoint)

        try:
            query_response = requests.post(url=url_publisher, headers=headers, data=data)
        except requests.exceptions.ConnectionError:
            raise XrayException(f"Cannot connect to JIRA service at {url_endpoint}")
        else:
            query_response.raise_for_status()

        return json.loads(query_response.content)

    def _publish_xml_result_multipart(
        self,
        token: str,
        data: dict,
        project_key: str,
        test_execution_name: str,
    ):
        # construct the request header
        headers = {"Authorization": "Bearer " + token}
        url_endpoint = "import/execution/junit/multipart"
        url_publisher = self.get_url(url_endpoint="import/execution/junit/multipart")
        files = {
            "info": json.dumps(
                {
                    "fields": {
                        "project": {"key": project_key},
                        "summary": test_execution_name,
                        "issuetype": {"name": "Xray Test Execution"},
                    }
                }
            ),
            "results": data,
            "testInfo": json.dumps(
                {
                    "fields": {
                        "project": {"key": project_key},
                        "summary": test_execution_name,
                        "issuetype": {"id": None},
                    }
                }
            ),
        }
        try:
            query_response = requests.post(url_publisher, headers=headers, files=files)
        except requests.exceptions.ConnectionError:
            raise XrayException(f"Cannot connect to JIRA service at {url_endpoint}")
        else:
            query_response.raise_for_status()
        return json.loads(query_response.content)


def upload_test_results(
    base_url: str,
    user: str,
    password: str,
    results: str,
    project_key: str,
    test_execution_id: str | None = None,
    test_execution_name: str | None = None,
) -> dict[str, str]:
    """
    Upload all given results to xray.

    :param base_url: the xray's base url
    :param user: the user's session id
    :param password: the user's password
    :param results: the test results
    :param test_execution_id: the xray's test execution ticket id where to import the test results,
        if none is specified a new test execution ticket will be created

    :return: the content of the post request to create the execution test ticket: its id, its key, and its issue
    """
    xray_publisher = XrayPublisher(base_url=base_url, client_id=user, client_secret=password)
    # authenticate: get the correct token from the authenticate endpoint
    url_authenticate = xray_publisher.get_url(url_endpoint="authenticate/")
    token = xray_publisher.get_token(url=url_authenticate)
    # publish: post request to send the junit xml result to the junit xml endpoint
    responses = xray_publisher.publish_xml_result(
        token=token,
        data=results,
        project_key=project_key,
        test_execution_id=test_execution_id,
        test_execution_name=test_execution_name,
    )
    return responses


def extract_test_results(path_results: Path, merge_xml_files: bool, update_description: bool) -> list[str]:
    """
    Extract the test results linked to an xray test key. Filter the JUnit xml files generated by the execution of tests,
    to keep only the results of tests marked with an xray decorator. A temporary file is created with the test results.

    :param path_results: the path to the xml files
    :param merge_xml_files: merge all the files to return only a list with one element
    :param update_description: if True update the test description format of the xml element to be imported in the xray
        ticket description, if False the test description format is not corrected and it is not imported

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
        # from the JUnit xml files, create a temporary file
        for file in file_to_parse:
            tree = ET.ElementTree()
            tree.parse(file)
            root = tree.getroot()
            # scan all the xml to keep the testsuite with the property "test_key"
            for testsuite in root.findall("testsuite"):
                testcase = testsuite.find("testcase")
                properties = testcase.find("properties")
                if properties is None:
                    # remove the testsuite not marked by the xray decorator
                    tree.getroot().remove(testsuite)
                    continue
                is_xray = False
                for property in properties.findall("property"):
                    if property.attrib.get("name") == "test_key":
                        is_xray = True
                        break
                if not is_xray:
                    # remove the testsuite not marked by the xray decorator
                    tree.getroot().remove(testsuite)

            if update_description:
                # update the test_description property element: name and value attributes become name with the description as property text
                for property in root.iter("property"):
                    if property.attrib.get("name") == "test_description":
                        test_description = property.attrib["value"]
                        del property.attrib["value"]
                        property.text = test_description

            with tempfile.TemporaryFile() as fp:
                tree.write(fp)
                fp.seek(0)
                xml_results.append(fp.read().decode())

        return xml_results
