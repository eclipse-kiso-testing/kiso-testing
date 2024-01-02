##########################################################################
# Copyright (c) 2010-2023 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Can Auxiliary
*************

:module: can_auxiliary

:synopsis: Auxiliary enables you to read write can messages which are defined in a dbc file.

The goal of this module is to be able to receive and send signals which are defined in dbc file.

.. currentmodule:: can_auxiliary
"""

import functools
import logging
from queue import Queue, Empty
import threading
import time
from contextlib import ContextDecorator
from typing import Any, Optional

from pykiso import Message
from pykiso.can_message import CanMessage
from pykiso.can_parser import CanMessageParser
from pykiso.connector import CChannel
from pykiso.exceptions import AuxiliaryNotStarted
from pykiso.interfaces.dt_auxiliary import (
    DTAuxiliaryInterface,
    close_connector,
    open_connector,
)
from pykiso.lib.auxiliaries.communication_auxiliary import (
    CommunicationAuxiliary,
)

log = logging.getLogger(__name__)


class CanAuxiliary(DTAuxiliaryInterface):
    """Auxiliary is used for reading and writing can messages defined in dbc file"""

    def __init__(self, com: CChannel, dbc_file: str, **kwargs):
        """Constructor.

        :param com: CChannel that supports raw communication over CAN
        """
        self.tx_task_on = False
        super().__init__(
            is_proxy_capable=True, tx_task_on=True, rx_task_on=True, **kwargs
        )

        self.recv_can_messages = {}
        self.channel = com
        path_to_dbf_file = dbc_file
        self.parser = CanMessageParser(path_to_dbf_file)
        self.can_messages = {}

    @open_connector
    def _create_auxiliary_instance(self) -> bool:
        """Open the connector communication.

        :return: True if the channel is correctly opened otherwise False
        """
        log.internal_info("Auxiliary instance created")
        return True

    @close_connector
    def _delete_auxiliary_instance(self) -> bool:
        """Close the connector communication.

        :return: always True
        """
        log.internal_info("Auxiliary instance deleted")
        return True

    def _receive_message(self, timeout_in_s: float = 0.1) -> None:
        """Trigger connector reception method and put received messages
        in the queue.

        :param timeout_in_s: maximum time in second to wait for a response
        """
        try:
            rcv_data = self.channel.cc_receive(timeout=timeout_in_s)
            if rcv_data.get("msg") is not None:
                log.internal_debug(f"received message '{rcv_data}' from {self.channel}")
                message_name = self.parser.dbc.get_message_by_frame_id(
                    rcv_data["remote_id"]
                ).name
                message_signals = self.parser.decode(
                    rcv_data["msg"], rcv_data["remote_id"]
                )
                message_timestamp = float(rcv_data.get("timestamp", 0))
                old_can_message = self.can_messages.get(message_name, None)
                if old_can_message is None:
                    self.can_messages[message_name] = Queue(maxsize=1)
                if not self.can_messages[message_name].empty():
                    self.can_messages[message_name].get(block=False)
                can_msg = CanMessage(
                        message_name, message_signals, message_timestamp
                    )
                self.can_messages[message_name].put(can_msg)
        except KeyError:
            #log.exception("Specific message signal is not found in message")
            pass
        except (Exception):
            #log.exception(
            #    f"encountered error while receiving message via {self.channel}"
            #)
            pass

    def get_last_message(self, message_name: str) -> Optional[CanMessage]:
        """Get the last message which has been received on the bus.
        :param message_name: name of the message, you want to get

        :return: last can massage or return none if the message, or return none if message is not occur
        """

        can_msg_queue = self.can_messages.get(message_name, None)
        if can_msg_queue is not None and not can_msg_queue.empty():
            msg = can_msg_queue.get()
            self.can_messages[message_name].put_nowait(msg)
            return msg
        return None
        

    def get_last_signal(self, message_name: str, signal_name: str) -> Optional[Any]:
        """Get the last message which has been received on the bus.
        :param message_name: name of the message, you want to get

        :return: last can massage or return none if the message or return none if message or signal is not occur
        """
        can_msg_queue = self.can_messages.get(message_name, None)
        if can_msg_queue is not None and not can_msg_queue.empty():
            last_can_message = can_msg_queue.get_nowait()
            if last_can_message is not None:
                self.can_messages[message_name].put_nowait(last_can_message)
                return last_can_message.signals[signal_name]
      
        return None
    def wait_for_message(
        self, message_name: str, timeout: float = 0.2
    ) -> dict[str, any]:
        """Get the last message with certain timeout in seconds.
        :param message_name: name of the message to receive
        :param timeout time to wait till a message receives in seconds

        :return: list of last can messages or None if no messages for this component
        """

        can_msg_queue = self.can_messages.get(message_name, None)
        old_value = None
        if can_msg_queue is None:
            self.can_messages[message_name] = Queue(maxsize=1)

        if not self.can_messages[message_name].empty():
            old_value = self.can_messages[message_name].get()

        try:
            new_msg = self.can_messages[message_name].get(timeout=timeout)
            self.can_messages[message_name].put_nowait(new_msg)
            return new_msg
        except Empty:
            if old_value is not None:
                self.can_messages[message_name].put_nowait(old_value)
            return None


    def wait_for_signal(
        self, message_name: str, expected_signals: dict[str, any], timeout: float = 0.2
    ) -> dict[str, any]:
        """Get the last signal of message with certain timeout in seconds.

        :param message_name: name of the message to receive
        :param signal_name: signal name in the message to receive
        :param timeout time to wait till a message receives in seconds

        :return: list of last can messages or None if no messages for this component
        """

        t1 = time.perf_counter()
        while time.perf_counter() - t1 < timeout:
            expected_signals_names = expected_signals.keys()
            last_msg_queue = self.can_messages.get(message_name, None)
            if last_msg_queue is None or last_msg_queue.empty():
                continue
            last_can_msg = last_msg_queue.get_nowait()
            for signal_name in expected_signals_names:
                if last_can_msg.signals[signal_name] != expected_signals[signal_name]:
                    continue
            return last_can_msg

        return None

    def send_message(self, message: str, signals: dict[str, Any]) -> bool:
        """Send one message, the message need to be defined in the dbc file.

        :param message: name of the message to send.
        :param signals: dict of the signals of the message and their value.

        :return: True or False if the message has been successfully send or not.
        """

        for signal, value in signals.items():
            if isinstance(value, str):
                signals[signal] = int.from_bytes(value.encode("utf8"), byteorder="big")
        try:
            message = self.parser.dbc.get_message_by_name(message)
        except KeyError:
            raise ValueError(f"{message} is not a message defined in the DBC file.")
        msg_to_send = self.parser.encode(message, signals)
        self.channel.cc_send(msg_to_send[0], remote_id=msg_to_send[1])

    def _run_command(self, cmd_message: str, cmd_data: bytes = None) -> bool:
        """Run the corresponding command.

        :param cmd_message: command type
        :param cmd_data: payload data to send over CChannel

        :return: True if command is executed otherwise False
        """
        if cmd_message == "send":
            try:
                self.channel.cc_send(msg=cmd_data)
            except Exception:
                log.exception(
                    f"encountered error while sending message '{cmd_data}' to {self.channel}"
                )
        elif isinstance(cmd_message, Message):
            log.internal_debug(f"ignored command '{cmd_message} in {self}'")
        else:
            log.internal_warning(f"received unknown command '{cmd_message} in {self}'")
