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

    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    with pytest.raises(
        XrayException, match="Cannot connect to JIRA service at https://example.com/api/v2/import/execution"
    ):
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
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")
    assert publisher.endpoint_url == "https://example.com/api/v2/import/execution"


@patch("pykiso.tool.xray.xray.requests.request")
def test_get_internal_id_from_key_success(mock_request):
    """Test successful retrieval of internal ID from Jira key."""
    # Mock the response
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"getTestExecutions": {"results": [{"issueId": "12345"}]}}}
    mock_request.return_value = mock_response

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method
    result = publisher.get_internal_id_from_key("TEST-123")

    # Verify the call was made correctly
    mock_request.assert_called_once()
    call_args = mock_request.call_args

    # Check that the authorization header contains the mock token
    assert "Authorization" in call_args.kwargs["headers"]
    assert "Bearer mock_token" in call_args.kwargs["headers"]["Authorization"]

    # Check the result
    assert result == "12345"


@patch("pykiso.tool.xray.xray.requests.request")
def test_get_internal_id_from_key_connection_error(mock_request):
    """Test ConnectionError handling in get_internal_id_from_key."""
    # Mock a ConnectionError
    mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method and expect an XrayException
    with pytest.raises(XrayException, match="Cannot connect to JIRA service at https://example.com/api/v2/graphql"):
        publisher.get_internal_id_from_key("TEST-123")

    # Verify the call was made
    mock_request.assert_called_once()


@patch("pykiso.tool.xray.xray.requests.request")
def test_get_internal_id_from_key_http_error(mock_request):
    """Test HTTP error handling in get_internal_id_from_key when raise_for_status is called."""
    # Mock the response with invalid data structure and HTTP error
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": "Invalid request"}  # Invalid response structure
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
    mock_request.return_value = mock_response

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method and expect an HTTPError to be raised
    with pytest.raises(requests.exceptions.HTTPError, match="401 Unauthorized"):
        publisher.get_internal_id_from_key("TEST-123")

    # Verify the call was made and raise_for_status was called
    mock_request.assert_called_once()
    mock_response.raise_for_status.assert_called_once()


@patch("pykiso.tool.xray.xray.requests.request")
def test_get_test_execution_results_success(mock_request):
    """Test successful retrieval of test execution results."""
    # Mock the response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": {
            "getTestExecution": {
                "tests": {"results": [{"issueId": "issue-1"}, {"issueId": "issue-2"}, {"issueId": "issue-3"}]}
            }
        }
    }
    mock_request.return_value = mock_response

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method
    result = publisher.get_test_execution_results("test-execution-123")

    # Verify the call was made correctly
    mock_request.assert_called_once()
    call_args = mock_request.call_args

    # Check that the authorization header contains the mock token
    assert "Authorization" in call_args.kwargs["headers"]
    assert "Bearer mock_token" in call_args.kwargs["headers"]["Authorization"]

    # Check the GraphQL query contains the test execution ID
    assert "test-execution-123" in call_args.kwargs["json"]["query"]

    # Check the result
    assert result == ["issue-1", "issue-2", "issue-3"]


@patch("pykiso.tool.xray.xray.requests.request")
def test_get_test_execution_results_connection_error(mock_request):
    """Test ConnectionError handling in get_test_execution_results."""
    # Mock a ConnectionError
    mock_request.side_effect = requests.exceptions.ConnectionError("Connection failed")

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method and expect an XrayException
    with pytest.raises(XrayException, match="Cannot connect to JIRA service at https://example.com/api/v2/graphql"):
        publisher.get_test_execution_results("test-execution-123")

    # Verify the call was made
    mock_request.assert_called_once()


@patch("pykiso.tool.xray.xray.requests.request")
def test_get_test_execution_results_http_error(mock_request):
    """Test HTTP error handling in get_test_execution_results when raise_for_status is called."""
    # Mock the response with invalid data structure and HTTP error
    mock_response = MagicMock()
    mock_response.json.return_value = {"error": "Invalid request"}  # Invalid response structure
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
    mock_request.return_value = mock_response

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method and expect an HTTPError to be raised
    with pytest.raises(requests.exceptions.HTTPError, match="404 Not Found"):
        publisher.get_test_execution_results("test-execution-123")

    # Verify the call was made and raise_for_status was called
    mock_request.assert_called_once()
    mock_response.raise_for_status.assert_called_once()


@patch("pykiso.tool.xray.xray.requests.request")
def test_get_jira_keys_for_tests_success(mock_request):
    """Test successful retrieval of Jira keys for tests."""
    # Mock the response for each request (one per issue ID)
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"getTest": {"jira": {"key": "TEST-123"}}}}
    mock_request.return_value = mock_response

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method with a list of issue IDs
    result = publisher.get_jira_keys_for_tests(["issue-1", "issue-2"])

    # Verify the calls were made correctly (should be 2 calls for 2 issue IDs)
    assert mock_request.call_count == 2

    # Check that all calls had the authorization header with the mock token
    for call in mock_request.call_args_list:
        assert "Authorization" in call.kwargs["headers"]
        assert "Bearer mock_token" in call.kwargs["headers"]["Authorization"]

    # Check the result (should return the same key for both issues based on our mock)
    assert result == ["TEST-123", "TEST-123"]


@patch("pykiso.tool.xray.xray.requests.request")
def test_get_jira_keys_for_tests_request_exception(mock_request):
    """Test RequestException handling in get_jira_keys_for_tests - should continue with next issue."""
    # Mock the first request to raise a RequestException, second to succeed
    mock_response_success = MagicMock()
    mock_response_success.json.return_value = {"data": {"getTest": {"jira": {"key": "TEST-456"}}}}

    mock_request.side_effect = [
        requests.exceptions.RequestException("Network error"),  # First call fails
        mock_response_success,  # Second call succeeds
    ]

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method with a list of issue IDs
    result = publisher.get_jira_keys_for_tests(["issue-1", "issue-2"])

    # Verify both calls were made
    assert mock_request.call_count == 2

    # Check the result (should only contain the key from the successful call)
    assert result == ["TEST-456"]


@patch("pykiso.tool.xray.xray.requests.request")
def test_get_jira_keys_for_tests_json_decode_error(mock_request):
    """Test JSONDecodeError handling in get_jira_keys_for_tests - should continue with next issue."""
    # Mock the first request to raise a JSONDecodeError, second to succeed
    mock_response_success = MagicMock()
    mock_response_success.json.return_value = {"data": {"getTest": {"jira": {"key": "TEST-789"}}}}

    mock_response_error = MagicMock()
    mock_response_error.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

    mock_request.side_effect = [
        mock_response_error,  # First call returns invalid JSON
        mock_response_success,  # Second call succeeds
    ]

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method with a list of issue IDs
    result = publisher.get_jira_keys_for_tests(["issue-1", "issue-2"])

    # Verify both calls were made
    assert mock_request.call_count == 2

    # Check the result (should only contain the key from the successful call)
    assert result == ["TEST-789"]


@patch("pykiso.tool.xray.xray.requests.request")
def test_get_jira_keys_for_tests_key_error(mock_request):
    """Test KeyError handling in get_jira_keys_for_tests - should continue with next issue."""
    # Mock responses where first has missing key structure, second succeeds
    mock_response_error = MagicMock()
    mock_response_error.json.return_value = {"data": {"getTest": {}}}  # Missing 'jira' key

    mock_response_success = MagicMock()
    mock_response_success.json.return_value = {"data": {"getTest": {"jira": {"key": "TEST-999"}}}}

    mock_request.side_effect = [
        mock_response_error,  # First call has missing key structure
        mock_response_success,  # Second call succeeds
    ]

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method with a list of issue IDs
    result = publisher.get_jira_keys_for_tests(["issue-1", "issue-2"])

    # Verify both calls were made
    assert mock_request.call_count == 2

    # Check the result (should only contain the key from the successful call)
    assert result == ["TEST-999"]


@patch("pykiso.tool.xray.xray.XrayInterface.get_jira_keys_for_tests")
@patch("pykiso.tool.xray.xray.XrayInterface.get_test_execution_results")
@patch("pykiso.tool.xray.xray.XrayInterface.get_internal_id_from_key")
def test_get_all_test_jira_keys_success(mock_get_internal_id, mock_get_test_results, mock_get_jira_keys):
    """Test successful retrieval of all Jira keys for tests in a test execution."""
    # Mock the method chain
    mock_get_internal_id.return_value = "internal-123"
    mock_get_test_results.return_value = ["issue-1", "issue-2", "issue-3"]
    mock_get_jira_keys.return_value = ["TEST-123", "TEST-456", "TEST-789"]

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method
    result = publisher.get_all_test_jira_keys("TEST-EXEC-123")

    # Verify the method chain was called correctly
    mock_get_internal_id.assert_called_once_with("TEST-EXEC-123")
    mock_get_test_results.assert_called_once_with("internal-123")
    mock_get_jira_keys.assert_called_once_with(["issue-1", "issue-2", "issue-3"])

    # Check the result
    assert result == ["TEST-123", "TEST-456", "TEST-789"]


@patch("pykiso.tool.xray.xray.XrayInterface.get_jira_keys_for_tests")
@patch("pykiso.tool.xray.xray.XrayInterface.get_test_execution_results")
@patch("pykiso.tool.xray.xray.XrayInterface.get_internal_id_from_key")
def test_get_all_test_jira_keys_empty_issue_ids(mock_get_internal_id, mock_get_test_results, mock_get_jira_keys):
    """Test get_all_test_jira_keys when get_test_execution_results returns empty list."""
    # Mock the method chain with empty issue_ids
    mock_get_internal_id.return_value = "internal-123"
    mock_get_test_results.return_value = []  # Empty list to trigger the early return

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Mock the auth object to return a token string when converted to string
    mock_auth = MagicMock()
    mock_auth.__str__ = MagicMock(return_value="mock_token")
    publisher.auth = mock_auth

    # Call the method
    result = publisher.get_all_test_jira_keys("TEST-EXEC-123")

    # Verify the method chain was called correctly up to the empty check
    mock_get_internal_id.assert_called_once_with("TEST-EXEC-123")
    mock_get_test_results.assert_called_once_with("internal-123")

    # get_jira_keys_for_tests should NOT be called when issue_ids is empty
    mock_get_jira_keys.assert_not_called()

    # Check the result is an empty list
    assert result == []


@patch("pykiso.tool.xray.xray.XrayInterface.publish_xml_result")
def test_upload_test_results(mock_publish_xml_result):
    """Test upload_test_results method - should delegate to publish_xml_result."""
    # Mock the publish_xml_result method
    mock_publish_xml_result.return_value = {"id": "123", "key": "TEST-EXEC-456", "issue": "Test Execution"}

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Test data
    test_data = {"testExecutionKey": "TEST-EXEC-456", "tests": [{"testKey": "TEST-123", "status": "PASS"}]}

    # Call the method
    result = publisher.upload_test_results(test_data)

    # Verify publish_xml_result was called with the correct data
    mock_publish_xml_result.assert_called_once_with(data=test_data)

    # Check the result
    assert result == {"id": "123", "key": "TEST-EXEC-456", "issue": "Test Execution"}


@patch("pykiso.tool.xray.xray.XrayInterface.get_all_test_jira_keys")
def test_get_jira_test_keys_from_test_execution_ticket(mock_get_all_test_jira_keys):
    """Test get_jira_test_keys_from_test_execution_ticket method - should delegate to get_all_test_jira_keys."""
    # Mock the get_all_test_jira_keys method
    mock_get_all_test_jira_keys.return_value = ["TEST-123", "TEST-456", "TEST-789"]

    # Create the publisher instance
    publisher = XrayInterface(base_url="https://example.com", client_id="user", client_secret="password")

    # Call the method
    result = publisher.get_jira_test_keys_from_test_execution_ticket("TEST-EXEC-123")

    # Verify get_all_test_jira_keys was called with the correct test execution ID
    mock_get_all_test_jira_keys.assert_called_once_with("TEST-EXEC-123")

    # Check the result
    assert result == ["TEST-123", "TEST-456", "TEST-789"]
