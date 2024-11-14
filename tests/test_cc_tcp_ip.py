##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

import socket

import pytest

from pykiso.lib.connectors import cc_tcp_ip

constructor_params = {"ip": "10.10.10.10", "port": 5000, "max_msg_size": 100}
example_message = "example message"
example_response = "example response"
query_value = {"query_value": "query_value"}
errors_to_catch = {
    "timeout": "timeout",
    "Exception": "Exception",
}


@pytest.fixture
def mock_socket(mocker):
    """Class used to mock socket.socket class"""

    class MockSocket:
        def __init__(self, address_family: int, socket_kind: int, **kwargs):
            self.address_family = address_family  # mock AddressFamily IntEnum
            self.socket_kind = socket_kind  # mock SocketKind IntEnum

        connect = mocker.stub(name="connect")
        close = mocker.stub(name="close")
        send = mocker.stub(name="send")
        settimeout = mocker.stub(name="settimeout")

        def recv(self, max_msg_size):
            # the max_msg_size parameter is used to trigger different scenarios
            if max_msg_size == query_value["query_value"]:
                response = "42.00 V"
            elif max_msg_size == errors_to_catch["timeout"]:
                raise socket.timeout("Timeout error raised")
            elif max_msg_size == errors_to_catch["Exception"]:
                raise Exception("Exception raised")
            else:
                response = example_response
            return response.encode()

    mocker.patch.object(cc_tcp_ip.socket, "socket", new=MockSocket)
    return cc_tcp_ip


@pytest.mark.parametrize(
    "constructor_params",
    [
        constructor_params,
    ],
)
def test_constructor(constructor_params):
    """Test constructor"""
    param = constructor_params.values()

    socket_connector = cc_tcp_ip.CCTcpip(*param)

    assert socket_connector.dest_ip == constructor_params["ip"]
    assert socket_connector.dest_port == constructor_params["port"]
    assert socket_connector.max_msg_size == constructor_params["max_msg_size"]
    assert socket_connector.timeout == 1e-6


@pytest.mark.parametrize(
    "constructor_params",
    [
        constructor_params,
    ],
)
def test__cc_open(mock_socket, constructor_params):
    """Test _cc_open"""
    param = constructor_params.values()
    socket_connector = cc_tcp_ip.CCTcpip(*param)

    socket_connector._cc_open()
    mock_socket.socket.socket.connect.assert_called_once()


@pytest.mark.parametrize(
    "constructor_params",
    [
        constructor_params,
    ],
)
def test__cc_close(mock_socket, constructor_params):
    """Test _cc_close"""
    param = constructor_params.values()
    socket_connector = cc_tcp_ip.CCTcpip(*param)
    socket_connector.open()
    socket_connector._cc_close()
    mock_socket.socket.socket.close.assert_called_once()


@pytest.mark.parametrize(
    "constructor_params, msg_to_send, expected_sent_message",
    [
        (constructor_params, "example", b"example"),
        (constructor_params, b"example", b"example"),
    ],
)
def test__cc_send(
    mock_socket,
    constructor_params,
    msg_to_send,
    expected_sent_message,
):
    """Test _cc_send"""
    param = constructor_params.values()
    socket_connector = cc_tcp_ip.CCTcpip(*param)
    socket_connector.open()
    socket_connector._cc_send(msg_to_send)
    mock_socket.socket.socket.send.assert_called_once_with(expected_sent_message)


@pytest.mark.parametrize(
    "constructor_params, expected_response, timeout, is_raw",
    [
        (constructor_params, {"msg": example_response}, 5, False),
        (constructor_params, {"msg": example_response.encode()}, 5, True),
        (constructor_params, {"msg": example_response.encode()}, 0, True),
        (constructor_params, {"msg": example_response.encode()}, None, True),
    ],
)
def test__cc_receive(
    mock_socket, constructor_params, expected_response, timeout, is_raw
):
    """Test _cc_receive"""
    param = constructor_params.values()
    socket_connector = cc_tcp_ip.CCTcpip(*param)
    socket_connector.open()

    socket_connector.socket.settimeout.reset_mock()
    response = socket_connector._cc_receive(timeout=timeout)
    if not is_raw:
        response["msg"] = response.get("msg").decode().strip()
    assert expected_response == response
    socket_connector.socket.settimeout.assert_called_once_with(timeout or 1e-6)


@pytest.mark.parametrize(
    "constructor_params, expected_response, is_raw",
    [
        (constructor_params, {"msg": example_response}, False),
    ],
)
def test__cc_receive_with_errors(
    mock_socket, constructor_params, expected_response, is_raw
):
    """Test _cc_receive with errors"""
    param = constructor_params.values()
    socket_connector = cc_tcp_ip.CCTcpip(*param)
    socket_connector.open()

    # using max_msg_size attribute tu trigger exceptions in mock
    for err in errors_to_catch:
        socket_connector.max_msg_size = err
        assert socket_connector._cc_receive() == {"msg": None}
