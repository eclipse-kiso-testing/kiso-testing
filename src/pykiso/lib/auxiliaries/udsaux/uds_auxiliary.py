##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
uds_auxiliary
*************

:module: uds_auxiliary

:synopsis: Auxiliary used to handle Unified Diagnostic Service protocol

.. currentmodule:: uds_auxiliary

"""
import logging
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Literal, Optional, Union, overload

try:
    import can
    from uds import IsoServices
except ImportError as e:
    raise ImportError(f"{e.name} dependency missing, consider installing pykiso with 'pip install pykiso[can]'")

from pykiso.connector import CChannel

from .common import uds_exceptions
from .common.uds_base_auxiliary import UdsBaseAuxiliary
from .common.uds_request import UDSCommands
from .common.uds_response import UdsResponse
from .common.uds_utils import get_uds_service

log = logging.getLogger(__name__)


class UdsAuxiliary(UdsBaseAuxiliary):
    """Auxiliary used to handle the UDS protocol on client (tester) side."""

    errors = uds_exceptions

    def __init__(
        self,
        com: CChannel,
        config_ini_path: Optional[Union[Path, str]] = None,
        odx_file_path: Optional[Union[Path, str]] = None,
        request_id: Optional[int] = None,
        response_id: Optional[int] = None,
        tp_layer: dict = None,
        uds_layer: dict = None,
        **kwargs,
    ):
        """Initialize attributes.
        :param com: communication channel connector.
        :param config_ini_path: UDS parameter file.
        :param odx_file_path: ecu diagnostic definition file.
        :param request_id: optional CAN ID used for sending messages.
        :param response_id: optional CAN ID used for receiving messages.
        :param tp_layer: isotp configuration given at yaml level
        :param uds_layer: uds configuration given at yaml level
        """
        self.is_tester_present = None
        super().__init__(
            com,
            config_ini_path,
            odx_file_path,
            request_id,
            response_id,
            tp_layer,
            uds_layer,
            **kwargs,
        )

    def transmit(self, data: bytes, req_id: int, extended: bool = False) -> None:
        """Transmit a message through ITF connector. This method is a
        substitute to transmit method present in python-uds package.

        :param data: data to send
        :param req_id: CAN message identifier
        :param extended: True if addressing mode is extended otherwise
            False
        """
        self.channel._cc_send(msg=data, remote_id=req_id)

    # Response is required, it is returned
    @overload
    def send_uds(
        self,
        msg_to_send: Union[bytes, List[int], tuple],
    ) -> UdsResponse:
        ...

    # Response is required, it is returned (explicit alias kept for backwards compatibility)
    @overload
    def send_uds(
        self,
        msg_to_send: Union[bytes, List[int], tuple],
        response_required: Literal[True] = True,
    ) -> UdsResponse:
        ...

    # Response ignored, `None` is returned
    @overload
    def send_uds(
        self,
        msg_to_send: Union[bytes, List[int], tuple],
        response_required: Literal[False] = False,
    ) -> None:
        ...

    def send_uds(
        self,
        msg_to_send: Union[bytes, List[int], tuple],
        response_required: bool = True,
    ) -> Union[UdsResponse, None]:
        """Send a UDS diagnostic request to the target ECU and check response.

        :param msg_to_send: can uds raw bytes to be sent
        :param response_required: Wait for a response if True

        :raise ResponseNotReceivedError: raised when no answer has been received
        :raise Exception: raised when the raw message could not be send properly

        :return: the raw uds response's bytes if `response_required` is set, else None
        """
        try:
            if log.isEnabledFor(logging.getLogger().level):
                log.internal_info(
                    "UDS request to send '%s'",
                    ["0x{:02X}".format(i) for i in msg_to_send],
                )
            resp = self.uds_config.send(
                msg_to_send,
                responseRequired=response_required,
                tpWaitTime=self.tp_waiting_time,
            )
        except Exception as exc:
            log.exception("Error while sending uds raw request")
            raise exc

        if resp is None:
            if not response_required:
                return
            else:
                raise self.errors.ResponseNotReceivedError(msg_to_send)

        resp = UdsResponse(
            resp,
            resp_time=self.uds_config.last_resp_time,
            pending_resp_times=self.uds_config.last_pending_resp_times,
        )
        log.internal_info("UDS response received %s", resp)
        return resp

    def send_uds_raw(
        self,
        msg_to_send: Union[bytes, List[int], tuple],
        timeout_in_s: float = 6,
        response_required: bool = True,
    ) -> Union[UdsResponse, bool]:
        """Send a UDS diagnostic request to the target ECU and check response.
        Deprecated alias of `send_uds` that returns `False` on error,
        kept for backwards compatibility

        :param msg_to_send: can uds raw bytes to be sent
        :param timeout_in_s: not used, actual timeout in seconds for the response can be
            configured with the uds_aux.config.uds_layer.p2_can_client parameter
            inside the yaml config file. (default value is 5s)
        :param response_required: Wait for a response if True

        :raise ResponseNotReceivedError: raised when no answer has been received

        :return: the raw uds response's bytes, or True if a response is
            not expected and the command is properly sent otherwise
            False
        """
        try:
            return self.send_uds(msg_to_send, response_required) or True
        except self.errors.ResponseNotReceivedError as exc:
            raise exc
        except Exception:
            return False

    @staticmethod
    def check_max_pending_time(resp: UdsResponse, max_pending_time: float) -> bool:
        """Check that the time between pending response messages does not exceed a
        max value

        :param resp: uds response to check
        :param max_pending_time: max pending time, in seconds

        :return: True if the max value is not exceeded, False otherwise
        """
        return max_pending_time >= max(resp.pending_resp_times)

    def check_raw_response_positive(self, resp: UdsResponse) -> Optional[bool]:
        """Check if the response is positive, raise an error if not

        :param resp: raw response of uds request

        :raise UnexpectedResponseError: raised when the answer is not the expected one

        :return: True if response is positive
        """
        if resp.is_negative:
            log.internal_info(f"Negative response with NRC: {resp.nrc.name}")
            raise self.errors.UnexpectedResponseError(resp)
        return True

    def check_raw_response_negative(self, resp: UdsResponse) -> Optional[bool]:
        """Check if the response is negative, raise an error if not

        :param resp: raw response of uds request

        :raise UnexpectedResponseError: raised when the answer is not the expected one

        :return: True if response is negative
        """
        if not resp.is_negative:
            raise self.errors.UnexpectedResponseError(resp)
        log.internal_info("Negative response with : %s", resp.nrc.name)
        return True

    def send_uds_config(
        self,
        msg_to_send: dict,
        timeout_in_s: float = 6,
    ) -> Union[dict, bool]:
        """Send UDS config to the target ECU.

        :param msg_to_send: uds config to be sent
        :param timeout_in_s: not used

        :return: a dict containing the uds response, or True if a
            response is not expected and the command is properly sent
            otherwise False
        """
        if not self.uds_config_enable:
            log.error("Uds configured without ODX, sending Uds config impossible!")
            return False

        try:
            uds_service_name = get_uds_service(msg_to_send["service"])
            uds_service = getattr(self.uds_config, uds_service_name)
            req_resp_data = uds_service(**msg_to_send["data"])
            if req_resp_data is None:
                req_resp_data = True
            log.internal_info("UDS response received %s", req_resp_data)
            return req_resp_data
        except AttributeError:
            # Service not found, raised by getattr()
            log.exception(f"Could not send UDS config request: unknown service {uds_service_name}")
            return False
        except Exception:
            # Data send failed
            log.exception("Could not send UDS config request: sending failed")
            return False

    def hard_reset(self) -> Union[dict, UdsResponse]:
        """Allow power reset of the component

        :return: response of the hard reset request
        """
        return self.send_uds_raw(UDSCommands.ECUReset.HARD_RESET)

    def force_ecu_reset(self) -> UdsResponse:
        """Allow power reset of the component

        :return: response of the force ecu reset request
        """
        if not self.uds_config_enable:
            return self.send_uds_raw(UDSCommands.ECUReset.KEY_OFF_ON_RESET)
        else:
            ecu_hard_reset_req = {
                "service": IsoServices.EcuReset,
                "data": {"parameter": "ForceEcuReset"},
            }
            return self.send_uds_config(ecu_hard_reset_req)

    def soft_reset(self) -> Union[dict, UdsResponse]:
        """Perform soft reset of the component, equivalent to a restart of application

        :return: response of the soft reset request
        """
        if not self.uds_config_enable:
            return self.send_uds_raw(UDSCommands.ECUReset.SOFT_RESET)
        else:
            ecu_soft_reset_req = {
                "service": IsoServices.EcuReset,
                "data": {"parameter": "Soft Reset"},
            }
            return self.send_uds_config(ecu_soft_reset_req)

    def read_data(self, parameter: str) -> Optional[Union[dict, bool]]:
        """UDS config command that allow data reading

        :param parameter: data to be read

        :return: a dict with uds config response
        """
        if self.uds_config_enable:
            req = {
                "service": IsoServices.ReadDataByIdentifier,
                "data": {
                    "parameter": parameter,
                },
            }
            return self.send_uds_config(req)
        else:
            log.error("No uds config found")
            return

    def write_data(self, parameter: str, value: Union[List[bytes], bytes]) -> Optional[Union[dict, bool]]:
        """UDS config command that allow data writing

        :param parameter: data to be set
        :param value: new content of the data

        :return: a dict with uds config response
        """
        if self.uds_config_enable:
            req = {
                "service": IsoServices.WriteDataByIdentifier,
                "data": {"parameter": parameter, "dataRecord": value},
            }
            return self.send_uds_config(req)
        else:
            log.error("No uds config found")
            return

    def _sender_run(self, period: int, stop_event: threading.Event) -> None:
        """send tester present at defined period until stopped

        :param period: period in seconds to use for the cyclic sending of tester present
        :param stop_event: event to set to stop the sending of tester present
        """
        while not stop_event.is_set():
            self.send_uds_raw(
                UDSCommands.TesterPresent.TESTER_PRESENT_NO_RESPONSE,
                response_required=False,
            )
            stop_event.wait(period)

    @contextmanager
    def tester_present_sender(self, period: int = 4) -> Iterator[None]:
        """Context manager that continuously sends tester present messages via UDS

        :param period: period in seconds to use for the cyclic sending of tester present
        """
        stop_event = threading.Event()
        sender = threading.Thread(
            name="TesterPresentSender",
            target=self._sender_run,
            args=(period, stop_event),
        )
        try:
            yield sender.start()
        finally:
            stop_event.set()
            sender.join()

    def start_tester_present_sender(self, period: int = 4):
        """Start to continuously send tester present messages via UDS"""
        if not self.is_tester_present:
            self.is_tester_present = self.tester_present_sender(period=period)
            return self.is_tester_present.__enter__()

    def stop_tester_present_sender(self):
        """Stop to continuously send tester present messages via UDS"""
        if self.is_tester_present:
            self.is_tester_present.__exit__(None, None, None)
            self.is_tester_present = None
        else:
            log.internal_warning("Tester present sender should be started before it can be stopped")

    def _receive_message(self, timeout_in_s: float) -> None:
        """This method is only used to populate the python-uds reception
        buffer. When a message is received, invoke python-uds configured
        callback to make it available for pyton-uds

        :param timeout_in_s: timeout on reception.
        """

        recv_response = self.channel.cc_receive(timeout=timeout_in_s)
        received_data = recv_response.get("msg")
        arbitration_id = recv_response.get("remote_id")

        if received_data is not None and arbitration_id == self.res_id:
            can_msg = can.Message(
                data=received_data,
                arbitration_id=arbitration_id,
                is_extended_id=False,
            )
            self.uds_config.tp.callback_onReceive(can_msg)

    def _run_command(self, cmd_message, cmd_data=None) -> Union[dict, bytes, bool]:
        """Not used."""
        pass

    def _delete_auxiliary_instance(self) -> bool:
        """Close current associated channel.

        :return: always True
        """
        if self.is_tester_present:
            self.stop_tester_present_sender()
        return super()._delete_auxiliary_instance()


# def uds() -> UdsAuxiliary:
#     raise NotImplementedError

# u: UdsAuxiliary = uds()
