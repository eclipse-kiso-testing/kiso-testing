import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from pykiso.tool.xray.xray import ClientSecretAuth, XrayException, XrayInterface, extract_test_results


def test_client_secret_auth_endpoint_url():
    auth = ClientSecretAuth(base_url="https://example.com/", client_id="id", client_secret="secret")
    assert auth.endpoint_url == "https://example.com/api/v2/authenticate"


@patch("pykiso.tool.xray.xray.requests.post")
def test_client_secret_auth_call(mock_post):
    mock_response = MagicMock()
    mock_response.text = '"token"'
    mock_post.return_value = mock_response

    auth = ClientSecretAuth(base_url="https://example.com", client_id="id", client_secret="secret")
    request = MagicMock()
    request.headers = {}
    auth(request)

    mock_post.assert_called_once_with(
        "https://example.com/api/v2/authenticate",
        data='{"client_id": "id", "client_secret": "secret"}',
        headers={"Content-type": "application/json", "Accept": "text/plain"},
        verify=True,
    )
    assert request.headers["Authorization"] == "Bearer token"


@patch("pykiso.tool.xray.xray.requests.request")
def test_publish_xml_result(mock_request):
    mock_response = MagicMock()
    mock_response.content = '{"id": "123", "key": "TEST-1", "issue": "Issue"}'
    mock_request.return_value = mock_response

    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")
    result = publisher.publish_xml_result(data={"key": "value"})

    mock_request.assert_called_once_with(
        method="POST",
        url="https://example.com/api/v2/import/execution",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"key": "value"},
        auth=publisher.auth,
        verify=True,
    )
    assert result == {"id": "123", "key": "TEST-1", "issue": "Issue"}


@patch("pykiso.tool.xray.xray.requests.request")
def test_publish_xml_result_connection_error(mock_request):
    mock_request.side_effect = requests.exceptions.ConnectionError

    publisher = XrayInterface(
        base_url="https://example.com",
        client_id="user",
        client_secret="password"
    )

    with pytest.raises(XrayException, match="Cannot connect to JIRA service at https://example.com/api/v2/import/execution"):
        publisher.publish_xml_result(data={"key": "value"})


def test_extract_test_results_with_valid_file(mocker):
    mocker.patch("pykiso.tool.xray.xray.create_result_dictionary", return_value={"key": "value"})
    mocker.patch("pykiso.tool.xray.xray.reformat_xml_results", return_value=["formatted_result"])

    xml_content = """<testsuites>
        <testsuite>
            <testcase classname="test_class" name="test_name" />
        </testsuite>
    </testsuites>"""

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as temp_file:
        temp_file.write(xml_content.encode())
        temp_file_path = Path(temp_file.name)

    results = extract_test_results(
        path_results=temp_file_path,
        merge_xml_files=False,
        jira_keys=[],
        test_execution_key=None,
    )

    assert results == ["formatted_result"]


def test_extract_test_results_with_invalid_file_extension():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
        temp_file_path = Path(temp_file.name)

    with pytest.raises(RuntimeError, match="Expected xml file but found a .txt file instead"):
        extract_test_results(
            path_results=temp_file_path,
            merge_xml_files=False,
            jira_keys=[],
            test_execution_key=None,
        )


def test_xray_exception_message():
    exception = XrayException(message="Test error message")
    assert exception.message == "Test error message"


@patch("pykiso.tool.xray.xray.requests.post")
def test_client_secret_auth_call_connection_error(mock_post):
    mock_post.side_effect = requests.exceptions.ConnectionError

    auth = ClientSecretAuth(base_url="https://example.com", client_id="test_id", client_secret="test_secret")
    request = MagicMock()

    with pytest.raises(
        XrayException, match="ConnectionError: cannot authenticate with https://example.com/api/v2/authenticate"
    ):
        auth(request)


@patch("pykiso.tool.xray.xray.requests.post")
def test_client_secret_auth_call_invalid_token(mock_post):
    mock_response = MagicMock()
    mock_response.text = '"invalid_token"'
    mock_post.return_value = mock_response

    auth = ClientSecretAuth(base_url="https://example.com", client_id="test_id", client_secret="test_secret")
    request = MagicMock()
    request.headers = {}

    auth(request)

    assert request.headers["Authorization"] == "Bearer invalid_token"


def test_xray_interface_endpoint_url():
    publisher = XrayInterface(
        base_url="https://example.com",
        client_id="user",
        client_secret="password"
    )
    assert publisher.endpoint_url == "https://example.com/api/v2/import/execution"
