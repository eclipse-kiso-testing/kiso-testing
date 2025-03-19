import json
import logging
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

import requests
from junitparser.cli import merge as merge_junit_xml
from requests.auth import AuthBase

API_VERSION = "api/v2/"
AUTHENTICATE_ENDPOINT = "/api/v2/authenticate"
XRAY_ENDPOINT = "api/v2/import/execution"


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

    def publish_xml_result(
        self,
        data: dict,
        project_key: str | None = None,
        test_execution_id: str | None = None,
        test_execution_name: str | None = None,
    ) -> dict[str, str]:
        """
        Publish the xml test results to xray.

        :param data: the test results
        :param project_key: the xray's project key
        :param test_execution_id: the xray's test execution ticket id where to import the test results,
            if none is specified a new test execution ticket will be created
        :param test_execution_name: the xray's test execution ticket summary
            if none is specified a `Execution of automated tests` is used
        :return: the content of the post request to create the execution test ticket: its id, its key, and its issue
        """
        if test_execution_name is None:
            return self._publish_xml_result(data=data)
        return self._publish_xml_result_multipart(
            data=data,
            project_key=project_key,
            test_execution_name=test_execution_name,
        )

    def _publish_xml_result(self, data: dict) -> dict[str, str]:
        # construct the request header
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        logging.info("Uploading test results to Xray...")
        try:
            query_response = requests.request(
                method="POST", url=self.endpoint, headers=headers, json=data, auth=self.auth, verify=self.verify
            )
        except requests.exceptions.ConnectionError:
            raise XrayException(f"Cannot connect to JIRA service at {self.endpoint}")
        else:
            query_response.raise_for_status()

        return json.loads(query_response.content)

    def _publish_xml_result_multipart(
        self,
        data: dict,
        project_key: str,
        test_execution_name: str,
    ):
        # TODO: _publish_xml_result_multipart to be removed?
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        # construct the request header
        url_endpoint = "import/execution/junit/multipart"
        url_publisher = f"{self.base_url}/{self.rest_api_version}{url_endpoint}"
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
    project_key: str | None = None,
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
    endpoint_url = base_url + XRAY_ENDPOINT
    # authenticate: get the correct token from the authenticate endpoint
    client_secret_auth = ClientSecretAuth(base_url=base_url, client_id=user, client_secret=password, verify=True)
    xray_publisher = XrayPublisher(base_url=base_url, endpoint=endpoint_url, auth=client_secret_auth)

    # publish: post request to send the test results to xray endpoint
    responses = xray_publisher.publish_xml_result(
        data=results,
        project_key=project_key,
        test_execution_id=test_execution_id,
        test_execution_name=test_execution_name,
    )
    return responses
