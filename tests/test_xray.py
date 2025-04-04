from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pykiso.tool.xray.xray import (
    ClientSecretAuth,
    XrayException,
    XrayPublisher,
    extract_test_results_from_junit,
    extract_test_results_from_pickle,
    upload_test_results,
)


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
def test_xray_publisher_publish_xml_result(mock_request):
    mock_response = MagicMock()
    mock_response.content = '{"id": "123", "key": "TEST-1", "issue": "Issue"}'
    mock_request.return_value = mock_response

    auth = MagicMock()
    publisher = XrayPublisher(base_url="https://example.com", endpoint="/endpoint", auth=auth)
    result = publisher.publish_xml_result(data={"key": "value"})

    mock_request.assert_called_once_with(
        method="POST",
        url="/endpoint",
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        json={"key": "value"},
        auth=auth,
        verify=True,
    )
    assert result == {"id": "123", "key": "TEST-1", "issue": "Issue"}


@patch("pykiso.tool.xray.xray.requests.post")
def test_upload_test_results(mock_post):
    mock_response = MagicMock()
    mock_response.text = '"token"'
    mock_post.return_value = mock_response

    mock_publisher = MagicMock()
    mock_publisher.publish_xml_result.return_value = {"id": "123", "key": "TEST-1", "issue": "Issue"}

    with patch("pykiso.tool.xray.xray.ClientSecretAuth", return_value=MagicMock()) as mock_auth, patch(
        "pykiso.tool.xray.xray.XrayPublisher", return_value=mock_publisher
    ):
        result = upload_test_results(
            base_url="https://example.com",
            user="user",
            password="password",
            results={"key": "value"},
        )

    mock_auth.assert_called_once_with(
        base_url="https://example.com", client_id="user", client_secret="password", verify=True
    )
    mock_publisher.publish_xml_result.assert_called_once_with(
        data={"key": "value"}, project_key=None, test_execution_id=None, test_execution_name=None
    )
    assert result == {"id": "123", "key": "TEST-1", "issue": "Issue"}


def test_extract_test_results_from_junit(tmp_path):
    xml_content = """<testsuites>
        <testsuite>
            <testcase>
                <properties>
                    <property name="test_key" value="TEST-1"/>
                </properties>
            </testcase>
        </testsuite>
    </testsuites>"""
    xml_file = tmp_path / "test.xml"
    xml_file.write_text(xml_content)

    results = extract_test_results_from_junit(path_results=xml_file, merge_xml_files=False, update_description=False)
    assert len(results) == 1
    assert "TEST-1" in results[0]


def test_extract_test_results_from_pickle(tmp_path):
    mock_deserialize = MagicMock(return_value={"key": "value"})
    with patch("pykiso.tool.xray.xray.deserialize_step_report", mock_deserialize):
        pkl_file = tmp_path / "test.pkl"
        pkl_file.write_bytes(b"mock content")

        results = extract_test_results_from_pickle(path_results=pkl_file)
        assert len(results) == 1
        assert results[0] == {"key": "value"}
        mock_deserialize.assert_called_once_with(pkl_file)
