##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Can Communication Channel SocketCAN
***********************************

:module: cc_socket_can

:synopsis: CChannel implementation for CAN(fd) using SocketCAN

.. currentmodule:: cc_socket_can

"""

import logging
import platform
import time
from pathlib import Path
from typing import Dict, Literal, Optional, Union

try:
    import can
    import can.bus
except ImportError as e:
    raise ImportError(f"{e.name} dependency missing, consider installing pykiso with 'pip install pykiso[can]'")


from pykiso import CChannel, Message
from pykiso.lib.connectors.cc_socket_can.socketcan_to_trc import SocketCan2Trc, can

MessageType = Union[Message, bytes]

log = logging.getLogger(__name__)


def os_name() -> str:
    """Returns the system/OS name.

    :return: os name such as 'Linux', 'Darwin', 'Java', 'Windows'
    """
    return platform.system()


class CCSocketCan(CChannel):
    """CAN FD channel-adapter."""

    def __init__(
        self,
        channel: str = "vcan0",
        remote_id: Optional[int] = None,
        is_fd: bool = True,
        enable_brs: bool = False,
        can_filters: Optional[list] = None,
        is_extended_id: bool = False,
        receive_own_messages: bool = False,
        logging_activated: bool = False,
        trace_path: Optional[str] = None,
        log_name: Optional[str] = None,
        strategy_trc_file: Optional[Literal["testRun", "testCase"]] = None,
        **kwargs,
    ):
        """Initialize can channel settings.

        :param channel: the can interface name. (i.e. vcan0, can1, ..)
        :param remote_id: id used for transmission
        :param is_fd: should the Bus be initialized in CAN-FD mode
        :param enable_brs: sets the bitrate_switch flag to use higher transmission speed
        :param can_filters: iterable used to filter can id on reception
        :param is_extended_id: this flag controls the size of the arbitration_id field
        :param receive_own_messages: if set transmitted messages will be received
        :param logging_activated: boolean used to enable logfile creation
        :param trace_path: trace directory path (absolute or relative), if you set a trc file name, auto timestamp and log_name will be ignored
        :param log_name: trace full name (without file extension)
        """
        super().__init__(**kwargs)
        self.channel = channel
        self.remote_id = remote_id
        self.is_fd = is_fd
        self.enable_brs = enable_brs
        self.can_filters = can_filters if can_filters else []
        self.is_extended_id = is_extended_id
        self.receive_own_messages = receive_own_messages
        self.logging_activated = logging_activated
        self.bus = None
        self.logger = None
        self.trace_path = trace_path
        self.log_name = log_name.strip(".trc") if log_name else None
        self.strategy_trc_file = strategy_trc_file
        self.opened = False

        # Set a timeout to send the signal to the GIL to change thread.
        # In case of a multi-threading system, all tasks will be called one after the other.
        self.timeout = 1e-6

        if self.logging_activated:
            self.resolve_trace_path()
        if self.enable_brs and not self.is_fd:
            log.internal_warning("Bitrate switch will have no effect because option is_fd is set to false.")

    def resolve_trace_path(self):
        """Resolve the trace path and name of the file that will be created for the trace"""
        # if no trace path is given, take the root path (where pykiso is launched)
        if self.trace_path is None or self.trace_path == "":
            self.trace_path = Path().resolve()

        # if the given log path is not absolute add root path
        # (where pykiso is launched) otherwise take it as it is
        self.trace_path = (
            Path().resolve() / self.trace_path if not Path(self.trace_path).is_absolute() else Path(self.trace_path)
        )

        # if specify a trace path with a file name, take the parent directory, ignore log_name and use the trc file as given.
        if self.trace_path.suffix == ".trc":
            self.log_name = self.trace_path.with_suffix("").name
            self.trace_path = self.trace_path.parent
        else:  # add timestamp to the log name other wise use timestamp with default name
            # add timestamp to the log name other wise use timestamp with default name
            self.log_name = (
                time.strftime(f"%Y-%m-%d_%H-%M-%S_{self.log_name}")
                if self.log_name is not None
                else time.strftime("%Y-%m-%d_%H-%M-%S_CanLog")
            )

        # create the trace path if it does not exist
        self.trace_path.mkdir(parents=True, exist_ok=True)
        self.log_name = f"{self.log_name}.trc"

    def _cc_open(self) -> None:
        """Open a can bus channel, set filters for reception and activate"""
        if self.opened:
            log.warning("Socket can is already opened")
            return
        if not os_name() == "Linux":
            raise OSError("socketCAN is only available under linux.")

        self.bus = can.interface.Bus(
            interface="socketcan",
            channel=self.channel,
            can_filters=self.can_filters,
            fd=self.is_fd,
            receive_own_messages=self.receive_own_messages,
        )

        if self.logging_activated:
            log.internal_info(f"Logging path for socketCAN set to {self.trace_path / self.log_name} ")
            self.logger = SocketCan2Trc(self.channel, str(self.trace_path / self.log_name))
            if self.strategy_trc_file is None:
                self.logger.start()
        self.opened = True

    def _cc_close(self) -> None:
        """Close the current can bus channel and close the log handler."""
        if not self.opened:
            log.warning("Socket can is already closed")
            return
        self.bus.shutdown()
        self.bus = None

        if self.logging_activated:
            self.logger.stop()
            self.logger = None

        self.opened = False

    def _cc_send(self, msg: MessageType, remote_id: int | None = None, **kwargs) -> None:
        """Send a CAN message at the configured id.
        If remote_id parameter is not given take configured ones

        :param msg: data to send
        :param remote_id: destination can id used

        """
        remote_id = remote_id or self.remote_id

        can_msg = can.Message(
            arbitration_id=remote_id,
            data=msg,
            is_extended_id=self.is_extended_id,
            is_fd=self.is_fd,
            bitrate_switch=self.enable_brs,
        )
        self.bus.send(can_msg)

        log.internal_debug(f"{self} sent CAN Message: {can_msg}, data: {msg}")

    def _cc_receive(self, timeout: float = 0.0001) -> Dict[str, Union[bytes, int]]:
        """Receive a can message using configured filters.

        :param timeout: timeout applied on reception

        :return: tuple containing the received data and the source can id
        """
        try:  # Catch bus errors & rcv.data errors when no messages where received
            received_msg = self.bus.recv(timeout=timeout or self.timeout)
            if received_msg is not None:
                frame_id = received_msg.arbitration_id
                payload = received_msg.data
                timestamp = received_msg.timestamp

                log.internal_debug("received CAN Message: {}, {}, {}".format(frame_id, payload, timestamp))
                return {"msg": payload, "remote_id": frame_id}
            else:
                return {"msg": None}
        except can.CanError as can_error:
            log.internal_debug(f"encountered can error: {can_error}")
            return {"msg": None}
        except Exception:
            log.exception(f"encountered error while receiving message via {self}")
            return {"msg": None}

    def stop_can_trace(self):
        """
        Stops the CAN trace if it is currently running.
        :return: None
        """
        if not self.logging_activated or self.logger is None:
            return

        self.logger.stop()

    def start_can_trace(self, trace_path: Optional[str] = None, log_name: Optional[str] = None) -> None:
        """Start the trace and write to the trace path written or the log name.

        :param trace_path: trace directory path (absolute or relative), if you set a trc file name, auto timestamp and log_name will be ignored,
            if not defined, will keep the directory path given in the configuration
        :param log_name: trace full name (without file extension)
        """
        if not self.logging_activated or self.logger is None:
            return

        if not self.logger.started:
            self.log_name = log_name.strip(".trc") if log_name else None
            if trace_path is not None:
                self.trace_path = trace_path
                self.resolve_trace_path()
            log.internal_info(f"Logging path for socketCAN set to {self.trace_path / self.log_name} ")
            self.logger.trc_file_name = str(self.trace_path / self.log_name)
            self.logger.start()
