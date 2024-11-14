##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

import importlib
import logging
import sys
import time
from pathlib import Path
from unittest import mock

import can as python_can
import pytest
from freezegun import freeze_time

from pykiso import Message
from pykiso.lib.connectors.cc_socket_can import cc_socket_can
from pykiso.lib.connectors.cc_socket_can.cc_socket_can import CCSocketCan, can
from pykiso.message import MessageCommandType, MessageType, TlvKnownTags

tlv_dict_to_send = {
    TlvKnownTags.TEST_REPORT: "OK",
    TlvKnownTags.FAILURE_REASON: b"\x12\x34\x56",
}

message_with_tlv = Message(
    msg_type=MessageType.COMMAND,
    sub_type=MessageCommandType.TEST_CASE_SETUP,
    test_suite=2,
    test_case=3,
    tlv_dict=tlv_dict_to_send,
)

message_with_no_tlv = Message(
    msg_type=MessageType.COMMAND,
    sub_type=MessageCommandType.TEST_CASE_SETUP,
    test_suite=2,
    test_case=3,
)


@pytest.fixture
def mock_can_bus(mocker):
    """fixture used to create mocker relative to can object from
    python-can package.
    """

    class MockCan:
        """Class used to stub can.interface.Bus method"""

        def __init__(self, **kwargs):
            """"""
            pass

        set_filters = mocker.stub(name="set_filters")
        shutdown = mocker.stub(name="shutdown")
        send = mocker.stub(name="send")
        recv = mocker.stub(name="recv")

    mocker.patch(
        "pykiso.lib.connectors.cc_socket_can.cc_socket_can.os_name",
        return_value="Linux",
    )
    mocker.patch.object(can.interface, "Bus", new=MockCan)
    return can.interface


def test_import():
    with pytest.raises(ImportError):
        sys.modules["can"] = None
        importlib.reload(cc_socket_can)
    sys.modules["can"] = can
    importlib.reload(cc_socket_can)


@pytest.mark.parametrize(
    "constructor_params, expected_config",
    [
        (
            {},
            {
                "channel": "vcan0",
                "remote_id": None,
                "is_fd": True,
                "enable_brs": False,
                "can_filters": [],
                "is_extended_id": True,
                "receive_own_messages": False,
                "logging_activated": False,
            },
        ),
        (
            {
                "channel": "vcan0",
                "remote_id": 0x666,
                "is_fd": False,
                "enable_brs": True,
                "can_filters": [
                    {"can_id": 0x507, "can_mask": 0x7FF, "extended": False}
                ],
                "is_extended_id": False,
                "receive_own_messages": True,
                "logging_activated": True,
            },
            {
                "channel": "vcan0",
                "remote_id": 0x666,
                "is_fd": False,
                "enable_brs": True,
                "can_filters": [
                    {"can_id": 0x507, "can_mask": 0x7FF, "extended": False}
                ],
                "is_extended_id": False,
                "receive_own_messages": True,
                "logging_activated": True,
            },
        ),
    ],
)
def test_constructor(constructor_params, expected_config, caplog):
    param = constructor_params.values()

    with caplog.at_level(logging.INTERNAL_WARNING):
        can_inst = CCSocketCan(*param)

    assert can_inst.channel == expected_config["channel"]
    assert can_inst.remote_id == expected_config["remote_id"]
    assert can_inst.is_fd == expected_config["is_fd"]
    assert can_inst.enable_brs == expected_config["enable_brs"]
    assert can_inst.can_filters == expected_config["can_filters"]
    assert can_inst.receive_own_messages == expected_config["receive_own_messages"]
    assert can_inst.logging_activated == expected_config["logging_activated"]

    if not can_inst.is_fd and can_inst.enable_brs:
        assert "Bitrate switch will have no effect" in caplog.text


@pytest.mark.parametrize(
    "logging_requested",
    [
        (True),
        (False),
    ],
)
def test_cc_open(logging_requested, mock_can_bus, mocker):

    mock_logger = mocker.patch(
        "pykiso.lib.connectors.cc_socket_can.cc_socket_can.SocketCan2Trc"
    )

    can_inst = CCSocketCan(logging_activated=logging_requested)
    can_inst._cc_open()

    assert isinstance(can_inst.bus, mock_can_bus.Bus) == True
    assert can_inst.bus != None

    if logging_requested:
        assert isinstance(can_inst.logger, mocker.MagicMock)
        assert mock_logger.mock_calls[1] == mock.call().start()
        mock_logger.assert_called_once()

@freeze_time("2015-10-21")
@pytest.mark.parametrize(
    "trace_path_dir, trace_path_dir_expected,log_name, log_name_expected",
    [

        ("./some_directory",Path().resolve()/"some_directory","CanLog.trc","CanLog.trc"),
        ("/some_directory",Path("/some_directory").resolve(),"CanLog.trc","CanLog.trc"),
        ("/some_directory/rama/",Path("/some_directory/rama/").resolve(),"CanLog.trc","CanLog.trc"),

        ("./some_directory/log.trc",Path().resolve()/"some_directory",None,"log.trc"), # if trace_path_dir is a file ignore log_name
        ("./some_directory/log.trc",Path().resolve()/"some_directory","CanLog.trc","log.trc"), # if trace_path_dir is a file ignore log_name
        ("./some_directory",Path().resolve()/"some_directory","CanLog","CanLog.trc"), # trc suffix shall be added when not specified
    ],
)
def test_log_path(trace_path_dir,trace_path_dir_expected,log_name,log_name_expected,mocker):
    mock_mkdir = mocker.patch("pathlib.Path.mkdir")
    can_inst = CCSocketCan(logging_activated=True,trace_path=trace_path_dir,log_name=log_name)

    frozen_time = "" if  str(trace_path_dir).endswith(".trc") else time.strftime(f"%Y-%m-%d_%H-%M-%S_")

    assert can_inst.trace_path == trace_path_dir_expected
    assert can_inst.log_name == frozen_time + log_name_expected

    assert can_inst.log_name.endswith(".trc")
    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)


def test_cc_open_wrong_os(mocker):

    mocker.patch(
        "pykiso.lib.connectors.cc_socket_can.cc_socket_can.os_name",
        return_value="Windows",
    )
    mock_logger = mocker.patch(
        "pykiso.lib.connectors.cc_socket_can.cc_socket_can.SocketCan2Trc"
    )

    can_inst = CCSocketCan()
    with pytest.raises(OSError, match=r"socketCAN is only available under linux"):
        can_inst._cc_open()


@pytest.mark.parametrize(
    "logging_requested",
    [
        (True),
        (False),
    ],
)
def test_cc_close(logging_requested, mock_can_bus, mocker):

    mock_logger = mocker.patch(
        "pykiso.lib.connectors.cc_socket_can.cc_socket_can.SocketCan2Trc"
    )

    can_inst = CCSocketCan(logging_activated=True)
    can_inst._cc_open()

    can_inst._cc_close()

    mock_can_bus.Bus.shutdown.assert_called_once()
    assert can_inst.bus == None

    assert can_inst.logger == None


@pytest.mark.parametrize(
    "message,remote_id",
    [
        (
            b"\x10\x36",
            0x0A,
        ),
        (
            b"\x10\x36",
            None,
        ),
        (
            b"\x10\x36",
            10,
        ),
        (
            b"",
            10,
        ),
        (
            message_with_tlv,
            0x0A,
        ),
        (
            message_with_no_tlv,
            0x0A,
        ),
        (message_with_no_tlv, None),
        (message_with_no_tlv, 36),
    ],
)
def test_cc_send(mock_can_bus, message, remote_id):
    if isinstance(message, Message):
        message = message.serialize()
    with CCSocketCan(remote_id=0x0A) as can:
        can._cc_send(message, remote_id=remote_id)

    mock_can_bus.Bus.send.assert_called_once()
    mock_can_bus.Bus.shutdown.assert_called_once()


@pytest.mark.parametrize(
    "raw_data, can_id, timeout , raw ,expected_type",
    [
        (b"\x40\x01\x03\x00\x01\x02\x03\x00", 0x500, 10, False, Message),
        (
            b"\x40\x01\x03\x00\x01\x02\x03\x09\x6e\x02\x4f\x4b\x70\x03\x12\x34\x56",
            0x207,
            None,
            None,
            Message,
        ),
        (b"\x40\x01\x03\x00\x02\x03\x00", 0x502, 10, True, bytearray),
        (b"\x40\x01\x03\x00\x02\x03\x00", 0x502, 0, True, bytearray),
    ],
)
def test_can_recv(mocker, mock_can_bus, raw_data, can_id, timeout, raw, expected_type):
    mock_bus_recv = mocker.patch(
        "can.interface.Bus.recv",
        return_value=python_can.Message(data=raw_data, arbitration_id=can_id),
    )
    with CCSocketCan() as can:
        response = can._cc_receive(timeout)
        msg_received = response.get("msg")
        id_received = response.get("remote_id")

    if not raw and msg_received is not None:
        msg_received = Message.parse_packet(msg_received)
    assert isinstance(msg_received, expected_type)
    assert id_received == can_id
    mock_can_bus.Bus.recv.assert_called_once_with(timeout=timeout or 1e-6)
    mock_can_bus.Bus.shutdown.assert_called_once()


@pytest.mark.parametrize(
    "raw_state",
    [
        True,
        False,
    ],
)
def test_can_recv_invalid(mocker, mock_can_bus, raw_state):

    mocker.patch("can.interface.Bus.recv", return_value=None)

    with CCSocketCan() as can:
        response = can._cc_receive(
            timeout=0.0001,
        )
        msg_received = response.get("msg")
        id_received = response.get("remote_id")
    if not raw_state and msg_received is not None:
        msg_received = msg_received.parse_packet()
    assert msg_received is None
    assert id_received is None


def test_can_recv_exception(mocker, mock_can_bus):

    mocker.patch("can.interface.Bus.recv", side_effect=ValueError)

    with CCSocketCan() as can:
        recv_msg = can._cc_receive(timeout=0.0001)

    assert recv_msg["msg"] is None
    assert recv_msg.get("remote_id") is None


def test_can_recv_can_error_exception(mocker, mock_can_bus):

    mocker.patch("can.interface.Bus.recv", side_effect=python_can.CanError)

    with CCSocketCan() as can:
        recv_msg = can._cc_receive(timeout=0.0001)

    assert recv_msg["msg"] is None
    assert recv_msg.get("remote_id") is None
