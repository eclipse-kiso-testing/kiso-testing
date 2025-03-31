##########################################################################
# Copyright (c) 2010-2023 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from pykiso.lib.auxiliaries.udsaux.common.uds_callback import UdsCallback
from pykiso.lib.auxiliaries.udsaux.uds_server_auxiliary import UdsServerAuxiliary

ODX_REQUEST = {
    "service": 0x22,  # IsoServices.ReadDataByIdentifier
    "data": {"parameter": "SoftwareVersion"},
}

ODX_RESPONSE = {"SoftwareVersion": "0.17.0"}


class TestUdsServerAuxiliary:
    uds_aux_instance_odx = None
    uds_aux_instance_raw = None

    @pytest.fixture(scope="function")
    def uds_server_aux_inst(self, mocker, ccpcan_inst):
        mocker.patch(
            "pykiso.auxiliary.AuxiliaryInterface.create_instance",
            return_value=None,
        )
        mocker.patch(
            "pykiso.auxiliary.AuxiliaryInterface.delete_instance",
            return_value=None,
        )
        mocker.patch(
            "pykiso.auxiliary.AuxiliaryInterface.run_command",
            return_value=None,
        )
        mocker.patch("pykiso.lib.auxiliaries.udsaux.uds_server_auxiliary.OdxParser")

        TestUdsServerAuxiliary.uds_aux_instance_odx = UdsServerAuxiliary(
            com=ccpcan_inst,
            request_id=0x123,
            odx_file_path="odx",
        )
        return TestUdsServerAuxiliary.uds_aux_instance_odx

    def test_constructor_no_odx(self, uds_server_aux_inst, ccpcan_inst):
        uds_server_inst = UdsServerAuxiliary(
            com=ccpcan_inst,
            request_id=0x123,
            response_id=0x321,
        )

        assert uds_server_inst._callbacks == {}
        assert uds_server_inst._callback_lock is not None
        assert uds_server_inst.req_id == 0x123
        assert uds_server_inst.res_id == 0x321

        uds_server_inst = UdsServerAuxiliary(com=ccpcan_inst)

        assert uds_server_inst.req_id == None
        assert uds_server_inst.res_id == None

    # NEW odx constructor
    def test_constructor_odx_new(self, uds_server_aux_inst, ccpcan_inst):
        uds_server_inst = UdsServerAuxiliary(
            com=ccpcan_inst,
            request_id=0x123,
            response_id=0x321,
            odx_file_path="dummy.odx",
        )

        assert uds_server_inst._callbacks == {}
        assert uds_server_inst._callback_lock is not None
        assert uds_server_inst.odx_parser is not None
        assert uds_server_inst.req_id == 0x123
        assert uds_server_inst.res_id == 0x321

    @pytest.mark.parametrize(
        "data_len, expected_padded_len",
        [(7, 8), (9, 12), (20, 20), (21, 24), (42, 48), (62, 64)],
    )
    def test__pad_message(self, data_len, expected_padded_len):
        msg = [1] * data_len
        padded_msg = UdsServerAuxiliary._pad_message(msg)

        assert len(padded_msg) == expected_padded_len
        assert all([el == UdsServerAuxiliary.CAN_FD_PADDING_PATTERN for el in padded_msg[data_len:]])

    @pytest.mark.parametrize("req_id, expected_req_id", [(None, 0x123), (0x42, 0x42)])
    def test_transmit(self, mocker, uds_server_aux_inst, req_id, expected_req_id):
        data = [1, 2, 3, 4]
        mock_pad = mocker.patch.object(uds_server_aux_inst, "_pad_message", return_value=data)
        mock_channel = mocker.patch.object(uds_server_aux_inst, "channel")

        uds_server_aux_inst.transmit(data, req_id)

        mock_pad.assert_called_with(data)
        mock_channel._cc_send.assert_called_with(msg=data, remote_id=expected_req_id)

    @pytest.mark.parametrize(
        "cc_receive_return, expected_received_data",
        [
            ({"msg": None, "remote_id": 0xAC}, None),
            ({"msg": b"DATA", "remote_id": 0xDC}, None),
            ({"msg": b"DATA", "remote_id": 0xAC}, b"DATA"),
        ],
    )
    def test_receive(self, mocker, uds_server_aux_inst, cc_receive_return, expected_received_data):
        mock_channel = mocker.patch.object(uds_server_aux_inst.channel, "_cc_receive", return_value=cc_receive_return)
        uds_server_aux_inst.res_id = 0xAC

        received_data = uds_server_aux_inst.receive()

        uds_server_aux_inst.channel._cc_receive.assert_called_with(timeout=0)
        assert received_data == expected_received_data

    def test_receive_with_timeout(self, mocker, uds_server_aux_inst):
        mock_channel = mocker.patch.object(
            uds_server_aux_inst.channel,
            "_cc_receive",
            side_effect=[{"msg": None, "remote_id": 0xAC}, {"msg": b"DATA", "remote_id": 0xAC}],
        )
        uds_server_aux_inst.res_id = 0xAC

        received_data = uds_server_aux_inst.receive(0.1)

        uds_server_aux_inst.channel._cc_receive.assert_called_with(timeout=0.1)
        assert received_data == b"DATA"

    def test_receive_with_timeout_reached(self, mocker, uds_server_aux_inst):
        mock_channel = mocker.patch.object(
            uds_server_aux_inst.channel,
            "_cc_receive",
            side_effect=[{"msg": None, "remote_id": 0xAD}, {"msg": b"DATA", "remote_id": 0xAD}],
        )
        uds_server_aux_inst.res_id = 0xAC
        timeout = 0.2
        mock_time = mocker.patch(
            "pykiso.lib.auxiliaries.udsaux.uds_server_auxiliary.time.time", side_effect=[1, 1.1, 1.4]
        )

        received_data = uds_server_aux_inst.receive(timeout)

        uds_server_aux_inst.channel._cc_receive.assert_called_with(timeout=timeout)
        assert received_data == None

    def test_send_response(self, mocker, uds_server_aux_inst):
        uds_mock = mocker.patch.object(uds_server_aux_inst, "uds_config")
        uds_mock.tp.encode_isotp.return_value = "NOT NONE"
        mock_transmit = mocker.patch.object(uds_server_aux_inst, "transmit")

        uds_server_aux_inst.send_response(b"plop")

        uds_mock.tp.encode_isotp.assert_called_with(b"plop", use_external_snd_rcv_functions=True)
        mock_transmit.assert_called_with("NOT NONE")

    @pytest.mark.parametrize(
        "stmin_in_ms, expected_stmin",
        [(0, 0), (1, 1), (127, 127), (0.1, 0xF1), (0.9, 0xF9), (0.10001, 0xF1)],
    )
    def test_encode_stmin(self, stmin_in_ms, expected_stmin):
        encoded_stmin = UdsServerAuxiliary.encode_stmin(stmin_in_ms)
        assert encoded_stmin == expected_stmin

    def test_encode_stmin_exception(self):
        with pytest.raises(ValueError):
            UdsServerAuxiliary.encode_stmin(-1)

    @pytest.mark.parametrize(
        "fs, bs, stmin, expected_flow_control",
        [
            (0, 0, 0, [0x30, 0x00, 0x00]),
            (1, 0x42, 0.1, [0x31, 0x42, 0xF1]),
            (0, 0, 0, [0x30, 0x00, 0x00]),
        ],
    )
    def test_send_flow_control(self, mocker, uds_server_aux_inst, fs, bs, stmin, expected_flow_control):
        mock_transmit = mocker.patch.object(uds_server_aux_inst, "transmit")

        uds_server_aux_inst.send_flow_control(fs, bs, stmin)

        mock_transmit.assert_called_with(expected_flow_control)

    @pytest.mark.parametrize(
        "callback_params, expected_callback_dict",
        [
            pytest.param(
                ([0x10, 0x11, 0x12], [0x12, 0x11, 0x10]),
                {"0x101112": UdsCallback([0x10, 0x11, 0x12], [0x12, 0x11, 0x10])},
                id="request and response passed",
            ),
            pytest.param(
                ([1, 2, 3], [3, 2, 1]),
                {"0x010203": UdsCallback([1, 2, 3], [3, 2, 1])},
                id="ensure trailing zero in dict key",
            ),
            pytest.param(
                ([0x10, 0x11, 0x12], None, [b"\xac\xdc"], 4),
                {"0x101112": UdsCallback([0x10, 0x11, 0x12], None, [b"\xac\xdc"], 4)},
                id="request and response data passed",
            ),
            pytest.param(
                UdsCallback([0x10, 0x11, 0x12], [0x12, 0x11, 0x10]),
                {"0x101112": UdsCallback([0x10, 0x11, 0x12], [0x12, 0x11, 0x10])},
                id="UdsCallback instance passed",
            ),
            # odx based callback registration
            pytest.param(
                UdsCallback(ODX_REQUEST, ODX_RESPONSE),
                {
                    "0x22A455": UdsCallback(
                        [0x22, 0xA4, 0x55],
                        [0x62, 0xA4, 0x55, 0x30, 0x2E, 0x31, 0x37, 0x2E, 0x30],
                    ),
                    "ReadDataByIdentifier.SoftwareVersion": UdsCallback(
                        [0x22, 0xA4, 0x55],
                        [0x62, 0xA4, 0x55, 0x30, 0x2E, 0x31, 0x37, 0x2E, 0x30],
                    ),
                },
                id="ODX based UdsCallback instance passed",
            ),
            pytest.param(
                (ODX_REQUEST, ODX_RESPONSE),
                {
                    "0x22A455": UdsCallback(
                        [0x22, 0xA4, 0x55],
                        [0x62, 0xA4, 0x55, 0x30, 0x2E, 0x31, 0x37, 0x2E, 0x30],
                    ),
                    "ReadDataByIdentifier.SoftwareVersion": UdsCallback(
                        [0x22, 0xA4, 0x55],
                        [0x62, 0xA4, 0x55, 0x30, 0x2E, 0x31, 0x37, 0x2E, 0x30],
                    ),
                },
                id="Passed odx keyword dict directly",
            ),
            pytest.param(
                (ODX_REQUEST),
                {
                    "0x22A455": UdsCallback([0x22, 0xA4, 0x55], [0x62, 0xA4, 0x55]),
                    "ReadDataByIdentifier.SoftwareVersion": UdsCallback([0x22, 0xA4, 0x55], [0x62, 0xA4, 0x55]),
                },
                id="Passed odx keyword dict directly no response given",
            ),
            pytest.param(
                (ODX_REQUEST, {"Negative": 17}),
                {
                    "0x22A455": UdsCallback([0x22, 0xA4, 0x55], [0x7F, 0x22, 0x11]),
                    "ReadDataByIdentifier.SoftwareVersion": UdsCallback([0x22, 0xA4, 0x55], [0x7F, 0x22, 0x11]),
                },
                id="Negative response given",
            ),
        ],
    )
    def test_register_callback(self, uds_server_aux_inst, callback_params, expected_callback_dict):
        mock_request = [34, 42069]
        mock_response = [98, 42069]
        uds_server_aux_inst.odx_parser.get_coded_values = MagicMock(side_effect=[mock_request, mock_response])

        if isinstance(callback_params, tuple):
            uds_server_aux_inst.register_callback(*callback_params)
        else:
            uds_server_aux_inst.register_callback(callback_params)
        assert uds_server_aux_inst._callbacks == expected_callback_dict

    @pytest.mark.parametrize(
        "callback_to_unregister, expected_callback_key",
        [
            pytest.param(
                [0x10, 0x11, 0xFF],
                "0x1011FF",
                id="based on a list of int",
            ),
            pytest.param(
                0x1011FF,
                "0x1011FF",
                id="based on an int",
            ),
            pytest.param(
                "0x1011FF",
                "0x1011FF",
                id="based on a hex string",
            ),
        ],
    )
    def test_unregister_callback(self, uds_server_aux_inst, callback_to_unregister, expected_callback_key):
        uds_server_aux_inst.register_callback(0x1011FF)
        assert isinstance(uds_server_aux_inst._callbacks.get(expected_callback_key), UdsCallback)

        uds_server_aux_inst.unregister_callback(callback_to_unregister)
        assert uds_server_aux_inst._callbacks.get(expected_callback_key) is None

    @pytest.mark.parametrize(
        "hex_key, odx_key",
        [
            pytest.param(
                "0x22A455",
                "ReadDataByIdentifier.SoftwareVersion",
            ),
        ],
    )
    def test_unregister_odx_based_callback(self, uds_server_aux_inst, hex_key, odx_key):
        mock_request = [34, 42069]
        mock_response = [98, 42069]
        uds_server_aux_inst.odx_parser.get_coded_values = MagicMock(side_effect=[mock_request, mock_response])

        uds_server_aux_inst.register_callback(ODX_REQUEST)
        assert isinstance(uds_server_aux_inst._callbacks.get(hex_key), UdsCallback)
        assert isinstance(uds_server_aux_inst._callbacks.get(odx_key), UdsCallback)
        assert uds_server_aux_inst._callbacks.get(hex_key) == uds_server_aux_inst._callbacks.get(odx_key)

        uds_server_aux_inst.unregister_callback(hex_key)
        assert uds_server_aux_inst._callbacks.get(hex_key) is None
        assert uds_server_aux_inst._callbacks.get(odx_key) is None

    def test_unregister_callback_not_found(self, uds_server_aux_inst, caplog):
        with caplog.at_level(logging.ERROR):
            uds_server_aux_inst.unregister_callback(0x4242)

        assert "Could not unregister callback" in caplog.text

    def test__receive_message(self, mocker, uds_server_aux_inst):
        mock_channel = mocker.patch.object(uds_server_aux_inst, "channel")
        mock_channel.cc_receive.return_value = {
            "msg": b"DATA",
            "remote_id": uds_server_aux_inst.res_id,
        }

        mock_uds_config = mocker.patch.object(uds_server_aux_inst, "uds_config")
        mock_uds_config.tp.decode_isotp.return_value = [1, 2, 3]

        mock_dispatch = mocker.patch.object(uds_server_aux_inst, "_dispatch_callback")

        uds_server_aux_inst._receive_message(10)

        mock_channel.cc_receive.assert_called_once_with(10)
        mock_uds_config.tp.decode_isotp.assert_called_once_with(
            received_data=b"DATA", use_external_snd_rcv_functions=True
        )
        mock_dispatch.assert_called_once_with([1, 2, 3])

    def test__receive_message_exception(self, caplog, mocker, uds_server_aux_inst):
        mock_channel = mocker.patch.object(uds_server_aux_inst, "channel")
        mock_channel.cc_receive.return_value = {
            "msg": b"DATA",
            "remote_id": uds_server_aux_inst.res_id,
        }

        mock_uds_config = mocker.patch.object(uds_server_aux_inst, "uds_config")
        mock_uds_config.tp.decode_isotp.side_effect = Exception("oopsi")

        mock_dispatch = mocker.patch.object(uds_server_aux_inst, "_dispatch_callback")

        with caplog.at_level(logging.ERROR):
            uds_server_aux_inst._receive_message(10)

        mock_channel.cc_receive.assert_called_once_with(10)
        mock_uds_config.tp.decode_isotp.assert_called_once_with(
            received_data=b"DATA", use_external_snd_rcv_functions=True
        )

        assert "oopsi" in caplog.text
        mock_dispatch.assert_not_called()

    def test__dispatch_callback(self, uds_server_aux_inst):
        callback_mock = MagicMock()
        callback_mock.request = [0x01]

        uds_server_aux_inst._callbacks = {"0x0102": callback_mock}

        received_request = [0x01, 0x02]
        uds_server_aux_inst._dispatch_callback(received_request)

        callback_mock.assert_called_once_with(received_request, uds_server_aux_inst)

    def test__dispatch_callback_no_callback(self, mocker, caplog, uds_server_aux_inst):
        mocker.patch.object(UdsServerAuxiliary, "callbacks", return_value=dict())

        received_request = [0x01, 0x02]
        with caplog.at_level(logging.INTERNAL_WARNING):
            uds_server_aux_inst._dispatch_callback(received_request)

        assert "Unregistered request received" in caplog.text

    @pytest.mark.parametrize(
        "odx_request, odx_response, coded_values, expected_callback",
        [
            pytest.param(
                ODX_REQUEST,
                None,
                [[34, 42069]],
                UdsCallback([0x22, 0xA4, 0x55], [0x62, 0xA4, 0x55]),
            ),
            pytest.param(
                [0x22, 0xA4, 0x55],
                ODX_RESPONSE,
                [[98, 42069]],
                UdsCallback(
                    [0x22, 0xA4, 0x55],
                    [0x62, 0xA4, 0x55, 0x30, 0x2E, 0x31, 0x37, 0x2E, 0x30],
                ),
            ),
            pytest.param(
                ODX_REQUEST,
                ODX_RESPONSE,
                [[34, 42069], [98, 42069]],
                UdsCallback(
                    [0x22, 0xA4, 0x55],
                    [0x62, 0xA4, 0x55, 0x30, 0x2E, 0x31, 0x37, 0x2E, 0x30],
                ),
            ),
        ],
    )
    def test__create_callback_from_odx(
        self,
        uds_server_aux_inst,
        odx_request,
        odx_response,
        coded_values,
        expected_callback,
    ):
        uds_server_aux_inst.odx_parser.get_coded_values = MagicMock(side_effect=coded_values)

        callback = uds_server_aux_inst._create_callback_from_odx(odx_request, odx_response)
        assert callback == expected_callback

    def test__create_callback_from_odx_parse_error(self, uds_server_aux_inst, caplog):
        mock_request = [35, 42069]
        mock_response = [98, 42069]
        uds_server_aux_inst.odx_parser.get_coded_values = MagicMock(side_effect=[mock_request, mock_response])

        with pytest.raises(ValueError):
            with caplog.at_level(logging.ERROR):
                callback = uds_server_aux_inst._create_callback_from_odx(ODX_REQUEST)

        assert "Given SID 34 does not match parsed SID 35" in caplog.text

    @pytest.mark.parametrize(
        "coded_values, uds_data",
        [
            ([34, 42069], [0x22, 0xA4, 0x55]),
            ([16, 3], [0x10, 0x03]),
        ],
    )
    def test__format_uds_data(self, uds_server_aux_inst, coded_values, uds_data):
        actual = uds_server_aux_inst._format_uds_data(coded_values)
        assert uds_data == actual

    @pytest.mark.parametrize(
        "request_dict, response_dict, expected_param,",
        [
            pytest.param(ODX_REQUEST, ODX_RESPONSE, "SoftwareVersion"),
            pytest.param(ODX_REQUEST, None, "SoftwareVersion"),
            pytest.param([0x22, 0xA4, 0x55], ODX_RESPONSE, "SoftwareVersion"),
        ],
    )
    def test__get_odx_callback_param(self, uds_server_aux_inst, request_dict, response_dict, expected_param):
        param = uds_server_aux_inst._get_odx_callback_param(request_dict, response_dict)
        assert param == expected_param
