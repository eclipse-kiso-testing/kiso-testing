##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Device Under Test Auxiliary
***************************

:module: DUTAuxiliary

:synopsis: The Device Under Test auxiliary allow to flash and run test
    on the target using the connector provided.

.. currentmodule:: dut_auxiliary

"""
import logging
from typing import Optional

from pykiso import AuxiliaryInterface, CChannel, Flasher, Message, message
from pykiso.lib.connectors.cc_rtt_segger import CCRttSegger
from pykiso.lib.connectors.cc_tcp_ip import CCTcpip
from pykiso.lib.connectors.cc_visa import VISAChannel

log = logging.getLogger(__name__)


class DUTAuxiliary(AuxiliaryInterface):
    """Device Under Test(DUT) auxiliary implementation."""

    def __init__(
        self,
        name: str = None,
        com: CChannel = None,
        flash: Flasher = None,
        **kwargs,
    ):
        """Constructor.

        :param name: Alias of the auxiliary instance
        :param com: Communication connector
        :param flash: flash connector
        """
        super().__init__(name=name, **kwargs)
        self.channel = com
        self.flash = flash
        self._is_suspend = False
        log.debug(f"com is {com}")
        log.debug(f"flash is {flash}")

    def _create_auxiliary_instance(self) -> bool:
        """Create auxiliary instance flash and connect.

        :return: True if everything was successful otherwise False
        """

        log.info("Create auxiliary instance")

        # Flash the device if flash connector provided
        if self.flash is not None and not self._is_suspend:
            log.info("Flash target")
            try:
                with self.flash as flasher:
                    flasher.flash()
            except Exception as e:
                # stop the thread if the flashing failed
                log.exception(f"Error occurred during flashing : {e}")
                log.fatal("Stopping the auxiliary")
                self.stop()
                return False  # Prevent to open channels by returning error state

        # Enable the communication through the connector
        log.info("Open channel communication")
        return_code = False
        try:
            self.channel.open()
        except Exception:
            log.exception("Unable to open channel communication")
            self.stop()
        else:
            # Ping-pong test
            return_code = self._send_ping_command(2, 1)

        # Return output
        return return_code

    def _delete_auxiliary_instance(self) -> bool:
        """Close the connector communication.

        :return: always True
        """

        log.info("Close the DUT auxiliary instance")
        self.channel.close()
        return True

    def suspend(self) -> None:
        """Suspend DutAuxiliary's run.

        Set _is_suspend flag to True to avoid a re-flash sequence.
        """
        self._is_suspend = True
        super().suspend()

    def resume(self) -> None:
        """Resume DutAuxiliary's run.

        Set _is_suspend flag to False in order to re-activate flash
        sequence in case of e.g. a futur abort command.
        """
        self._is_suspend = False
        super().resume()

    def _run_command(
        self, cmd_message: message.Message, cmd_data: bytes = None
    ) -> bool:
        """Run a command for the auxiliary.

        :param cmd_message: command in form of a message to run
        :param cmd_data: payload data for the command

        :return: True - Successfully received bv the instance / False - Failed sending
        """

        log.info(f"Send test request: {cmd_message}")
        return self._send_and_wait_ack(cmd_message, 2, 2)

    def _abort_command(self) -> bool:
        """Send an abort command and reset the auxiliary if needed.

        :return: True if ACK is received otherwise False
        """

        log.info("Send abort request")
        # Try a soft abort
        msg = message.Message(
            message.MessageType.COMMAND, message.MessageCommandType.ABORT
        )  # TODO verify if this generation can happened somewhere else
        result = self._send_and_wait_ack(msg, 2, 2)
        # If not successful, do hard reset
        if result is False:
            self._delete_auxiliary_instance()
            self._create_auxiliary_instance()
        return result

    def _receive_message(
        self, timeout_in_s: float, raw: bool = True
    ) -> message.Message:
        """Get message from the device under test.

        :param timeout_in_s: Time in ms to wait for one try
        :param raw: if raw is True the message is raw bytes, otherwise Message type like

        :returns: receive message
        """
        # Read message on the channel
        received_message = self._receive_msg(timeout_in_s=timeout_in_s, raw=raw)
        if received_message is not None:
            # Send ack
            msg_to_send = received_message.generate_ack_message(
                message.MessageAckType.ACK
            )
            self._send_message(message_to_send=msg_to_send, raw=raw)
            # Return message
            return received_message

    def _send_ping_command(self, timeout: int, tries: int, raw: bool = True) -> bool:
        """Ping Pong test to confirm the communication state.

        :param timeout: Time in ms to wait for one try
        :param tries: Number of tries to send the message

        :return: True if the target answer
        """
        number_of_tries = 0
        is_pong_ack = False

        # Empty memory in case target start by sending a message
        self._receive_msg(timeout_in_s=1, raw=raw)
        # Try Ping-Pong
        while number_of_tries < tries:
            log.info(f"Ping-Pong try n: {number_of_tries}")

            # Increase number of tries
            number_of_tries += 1

            # Send a ping message
            ping_request = message.Message(test_suite=0, test_case=0)
            self._send_message(message_to_send=ping_request, raw=raw)

            # Receive the message
            pong_response = self._receive_msg(timeout_in_s=timeout, raw=raw)

            # Validate ping pong
            log.debug(f"ping: {ping_request}")
            log.debug(f"pong: {pong_response}")
            # testing if is tuple instance to avoid infinite loop when
            # DUT auxiliary is bounded with a proxy auxiliary
            if pong_response is not None and not isinstance(pong_response, tuple):
                if ping_request.check_if_ack_message_is_matching(pong_response):
                    log.info("Ping-Pong succeed")
                    is_pong_ack = True
                    break
                else:
                    log.warning(
                        f"Received {pong_response} not matching {ping_request}!"
                    )
                    continue  # A NACK got received # TODO later on we should have "not supported" and ignore it than.

        return is_pong_ack

    def _send_and_wait_ack(
        self,
        message_to_send: message.Message,
        timeout: int,
        tries: int,
        raw: bool = False,
    ) -> bool:
        """Send via the channel a message and wait for an acknowledgement.

        :param message_to_send: Message you want to send out
        :param timeout: Time in ms to wait for one try
        :param tries: Number of tries to send the message

        :returns: True - Ack, False - Nack
        """

        number_of_tries = 0
        result = False

        while number_of_tries < tries:
            log.info(f"Run send try n: {number_of_tries}")

            # Increase number of tries
            number_of_tries += 1

            # Send the message
            self._send_message(message_to_send, raw)

            received_message = self._receive_msg(timeout, raw)

            # Check the outcome
            if received_message is None:
                continue  # Next try will occur
            else:
                log.debug(f"message_to_send  {message_to_send}")
                log.debug(f"received_message {received_message}")
                if message_to_send.check_if_ack_message_is_matching(received_message):
                    log.info(f"{message_to_send} sent")
                    result = True
                    break
                else:
                    log.warning(
                        f"Received {received_message} not matching with {message_to_send}!"
                    )
                    continue  # A NACK got received # TODO later on we should have "not supported" and ignore it than.
        return result

    def _send_message(self, message_to_send: message.Message, raw: bool = False):
        """Function to modify the message if we want it raw or not.

        :param message_to_send: Message you want to send out
        :param tries: Number of tries to send the message

        """
        # We serialize the message if raw is false and we sent it
        if not raw and isinstance(message_to_send, Message):
            message_to_send = message_to_send.serialize()
        # This channel doesn't serialize the message but encode it

        self.channel.cc_send(msg=message_to_send)

    def _receive_msg(
        self, timeout_in_s: float, raw: bool = False, size: Optional[int] = None
    ):
        """Receive the message and return it raw if wanted or a Message and
        treat the case where the channel is cc_rtt_segger

        :param timeout_in_s: Time in ms to wait for one try
        :param raw: if raw is True the message is raw bytes, otherwise Message type like

        :returns: receive message
        """
        # Those channel treat the messages differently so we keep the raw
        if isinstance(self.channel, (CCRttSegger)) and not raw:
            size = Message().header_size

        if isinstance(self.channel, (VISAChannel)):
            recv_response = self.channel.cc_receive(timeout_in_s, raw)
        else:
            recv_response = self.channel.cc_receive(timeout_in_s, size=size)

        msg_received = recv_response.get("msg")
        if not raw and msg_received is not None and isinstance(msg_received, bytes):
            msg_received = Message.parse_packet(msg_received)
        elif not raw and isinstance(self.channel, CCTcpip):
            msg_received = msg_received.decode().strip()

        return msg_received
