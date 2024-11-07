##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Auxiliary common Interface Definition
*****************************************

:module: auxiliary
:synopsis: base auxiliary interface

.. currentmodule:: pykiso

"""
import abc
import enum
import functools
import logging
import queue
import threading
from enum import Enum, unique
from typing import Any, Callable, List, Optional

from typing_extensions import Self

from pykiso.test_setup.config_registry import ConfigRegistry

from .exceptions import AuxiliaryCreationError, AuxiliaryNotStarted
from .logging_initializer import add_internal_log_levels, initialize_loggers

log = logging.getLogger(__name__)


@unique
class AuxCommand(Enum):
    """Contain all available auxiliary's commands."""

    #: create auxiliary command id
    CREATE_AUXILIARY = enum.auto()
    #: delete auxiliary command id
    DELETE_AUXILIARY = enum.auto()


class AuxiliaryInterface(abc.ABC):
    """Common interface for all double threaded auxiliary. A so called
    << double threaded >> auxiliary, simply encapsulate two threads one
    for the reception and one for the transmmission.
    """

    @classmethod
    def get_instance(cls, name: str) -> Self:
        """Experimental - Get an auxiliary instance by its name."""
        auxiliary = ConfigRegistry.get_aux_by_alias(name)
        # Verify if the auxiliary is of the right type
        if not isinstance(auxiliary, cls):
            raise ValueError(f"Requested auxiliary {name} is not of type {cls}")
        return auxiliary

    def __init__(
        self,
        name: str = None,
        is_proxy_capable: bool = False,
        connector_required: bool = True,
        activate_log: List[str] = None,
        tx_task_on=True,
        rx_task_on=True,
        auto_start: bool = True,
    ) -> None:
        """Initialize auxiliary attributes

        :param name: alias of the auxiliary instance
        :param is_proxy_capable: notify if the current auxiliary could
            be (or not) associated to a proxy-auxiliary.
        :param connector_required: define if a connector is required for
            this auxiliary.
        :param activate_log: loggers to deactivate
        :param tx_task_on: enable or not the tx thread
        :param rx_task_on: enable or not the rx thread
        :param auto_start: determine if the auxiliayry is automatically
             started (magic import) or manually (by user)
        """
        initialize_loggers(activate_log)
        add_internal_log_levels()
        self.name = name
        self.is_proxy_capable = is_proxy_capable
        self.auto_start = auto_start
        self.lock = threading.RLock()
        self.rx_lock = threading.Lock()
        self._stop_event = threading.Event()
        self.stop_tx = threading.Event()
        self.stop_rx = threading.Event()
        self.queue_in = queue.Queue()
        self.queue_out = queue.Queue()
        self.tx_task_on = tx_task_on
        self.rx_task_on = rx_task_on
        self.tx_thread = None
        self.rx_thread = None
        self.recv_timeout = 1
        self.is_instance = False
        self.connector_required = connector_required

    def run_command(
        self,
        cmd_message: Any,
        cmd_data: Any = None,
        blocking: bool = True,
        timeout_in_s: int = 5,
        timeout_result: Any = None,
    ) -> Any:
        """Send a request by transmitting it through queue_in and
        waiting for a response using queue_out.

        :param cmd_message: command request to the auxiliary
        :param cmd_data: data you would like to populate the command
            with
        :param blocking: If you want the command request to be
            blocking or not
        :param timeout_in_s: Number of time (in s) you want to wait
            for an answer
        :param timeout_result: Value to return when the command times
            out. Defaults to None.

        :raises pykiso.exceptions.AuxiliaryNotStarted: if a command is
            executed although the auxiliary was not started.
        :return: True if the request is correctly executed otherwise
            False
        """
        # avoid a deadlock in case run_command is called within a _receive_message implementation
        # (for e.g. callback implementation) while delete_instance is being executed from the main thread
        if self._stop_event.is_set():
            return timeout_result

        with self.lock:
            if not self.is_instance:
                raise AuxiliaryNotStarted(self.name)

            log.internal_debug(f"sending command '{cmd_message}' with payload {cmd_data} using {self.name} aux.")
            response_received = timeout_result
            self.queue_in.put((cmd_message, cmd_data))
            try:
                response_received = self.queue_out.get(blocking, timeout_in_s)
                log.internal_debug(f"reply to command '{cmd_message}' received: '{response_received}' in {self.name}")
            except queue.Empty:
                log.error(
                    f"no reply received within time for command {cmd_message} for payload {cmd_data} using {self.name} aux."
                )
        return response_received

    def create_instance(self) -> bool:
        """Start auxiliary's running tasks and activities.

        :return: True if the auxiliary is created otherwise False

        :raises AuxiliaryCreationError: if instance creation failed
        """
        log.internal_info(f"Creating instance of auxiliary {self.name}")

        with self.lock:
            # if the current aux is alive don't try to create it again
            if self.is_instance:
                log.internal_info(f"Auxiliary {self.name} is already created")
                return True

            is_created = self._create_auxiliary_instance()

            if not is_created:
                raise AuxiliaryCreationError(self.name)

            # start each auxiliary's tasks
            self._start_tx_task()
            self._start_rx_task()

            self.is_instance = True
            return is_created

    def delete_instance(self) -> bool:
        """Stop auxiliary's running tasks and activities.

        :return: True if the auxiliary is deleted otherwise False
        """
        log.internal_info(f"Deleting instance of auxiliary {self.name}")

        with self.lock:
            self._stop_event.set()
            # if the current aux is not alive don't try to delete it again
            if not self.is_instance:
                log.internal_info(f"Auxiliary {self.name} is already deleted")
                self._stop_event.clear()
                return True

            # stop each auxiliary's tasks
            self._stop_tx_task()
            self._stop_rx_task()

            is_deleted = self._delete_auxiliary_instance()

            if not is_deleted:
                log.error(f"Unexpected error occurred during deletion of auxiliary instance {self.name}")

            self.is_instance = False
            self._stop_event.clear()
            return is_deleted

    def _start_tx_task(self) -> None:
        """Start transmission task."""
        if self.tx_task_on is False:
            log.internal_debug("transmit task is not needed, don't start it")
            return

        task_name = f"{self.name}_tx"
        log.internal_debug("start transmit task %s", task_name)
        # Any created thread should disappear after main-thread exit
        self.tx_thread = threading.Thread(name=task_name, target=self._transmit_task, daemon=True)
        self.tx_thread.start()

    def _start_rx_task(self) -> None:
        """Start reception task."""
        if self.rx_task_on is False:
            log.internal_debug("reception task is not needed, don't start it")
            return
        with self.rx_lock:
            task_name = f"{self.name}_rx"
            log.internal_debug("start reception task %s", task_name)
            # Any created thread should disappear after main-thread exit
            self.rx_thread = threading.Thread(name=task_name, target=self._reception_task, daemon=True)
            self.rx_thread.start()

    def _stop_tx_task(self) -> None:
        """Stop transmission task."""
        if self.tx_task_on is False:
            log.internal_debug("transmit task was not started, no need to stop it")
            return

        log.internal_debug(f"stop transmit task {self.name}_tx")
        self.queue_in.put((AuxCommand.DELETE_AUXILIARY, None))
        self.stop_tx.set()
        self.tx_thread.join()
        self.stop_tx.clear()

    def _stop_rx_task(self) -> None:
        """Stop reception task."""
        if self.rx_task_on is False:
            log.internal_debug("reception task was not started, no need to stop it")
            return
        with self.rx_lock:
            log.internal_debug(f"stop reception task {self.name}_rx")
            self.stop_rx.set()
            self.rx_thread.join()
            self.stop_rx.clear()

    def start(self) -> bool:
        """Force the auxiliary to start all running tasks and
        activities.

        .. warning:: due to the usage of create_instance if an issue
            occurred the exception AuxiliaryCreationError is raised.

        :return: True if the auxiliary is started otherwise False
        """

        return self.create_instance()

    def stop(self) -> bool:
        """Force the auxiliary to stop all running tasks and activities.

        :return: True if the auxiliary is stopped otherwise False
        """
        return self.delete_instance()

    def __enter__(self) -> Self:
        """Context manager entry point"""
        if self.start():
            return self
        else:
            raise AuxiliaryNotStarted(f"Failed to start auxiliary {self.name}")

    def __exit__(self, type, value, traceback):
        """Context manager exit point"""
        stop_status = self.stop()
        if traceback:
            log.error(f"Error occurred during auxiliary {self.name} execution: {type=}, {value=}, {traceback=}")
        if not stop_status:
            raise RuntimeError(f"Failed to stop auxiliary {self.name}")

    def suspend(self) -> bool:
        """Supend current auxiliary's run.

        :return: True if the auxiliary is suspend otherwise False
        """
        return self.delete_instance()

    def resume(self) -> bool:
        """Resume current auxiliary's run.

        .. warning:: due to the usage of create_instance if an issue
            occurred the exception AuxiliaryCreationError is raised.

        :return: True if the auxiliary is resumed otherwise False
        """
        return self.create_instance()

    def _transmit_task(self) -> None:
        """Auxiliary transmission task.

        Simply call the child defined _run_command.
        """
        while not self.stop_tx.is_set():
            cmd, data = self.queue_in.get()
            # just stop the current Tx thread task
            if cmd == AuxCommand.DELETE_AUXILIARY:
                break

            self._run_command(cmd, data)

    def _reception_task(self) -> None:
        """Auxiliary reception task.

        Simply call the child defined _receive_message method.
        """
        while not self.stop_rx.is_set():
            self._receive_message(timeout_in_s=self.recv_timeout)

    def wait_for_queue_out(self, blocking: bool = False, timeout_in_s: int = 0) -> Optional[Any]:
        """Wait for data from the queue out.

        :param blocking: True: wait for timeout to expire, False: return
            immediately
        :param timeout_in_s: if blocking, wait the defined time in
            seconds

        :return: data contained in the auxiliary's queue_out
        """
        try:
            return self.queue_out.get(blocking, timeout_in_s)
        except queue.Empty:
            return None

    def shutdown(self):
        """Uninitialize method. Will be called at the end of the test session."""
        pass

    @abc.abstractmethod
    def _create_auxiliary_instance(self) -> bool:
        """Common interface call at auxiliary creation.

        This method could be used to e.g initiate the communication
        using the attached connector.

        :return: True - Successfully created / False - Failed by creation
        """

    @abc.abstractmethod
    def _delete_auxiliary_instance(self) -> bool:
        """Common interface call at auxiliary deletion.

        This method could be used to e.g terminate the current running
        communication...

        :return: True - Successfully deleted / False - Failed deleting
        """

    @abc.abstractmethod
    def _run_command(self, cmd_message: Any, cmd_data: Optional[bytes]) -> None:
        """Run a command for the auxiliary.

        :param cmd_message: command to send
        :param cmd_data: payload data for the command
        """

    @abc.abstractmethod
    def _receive_message(self, timeout_in_s: float) -> None:
        """Defines what needs to be done as a receive message. Such as,
         what do I need to do to receive a message.

        :param timeout_in_s: How much time to block on the receive
        """


def open_connector(func: Callable) -> Callable:
    """Open current associated auxiliary's channel.

    :param func: decorated method

    :return: inner decorated function
    """

    @functools.wraps(func)
    def inner_open(self, *arg, **kwargs) -> bool:
        """Open the channel.

        :param args: positional arguments
        :param kwargs: named arguments

        :return: True if everything was successful otherwise False
        """
        log.internal_info(f"Open {self.channel.__class__.__name__} channel {self.channel.name!r}")
        try:
            self.channel.open()
            return func(self, *arg, **kwargs)
        except Exception:
            log.exception(
                f"Unable to open {self.channel.__class__.__name__} channel communication for {self.channel.name!r}"
            )
            return False

    return inner_open


def close_connector(func: Callable) -> Callable:
    """Close current associated auxiliary's channel.

    :param func: decorated method

    :return: inner decorated function
    """

    @functools.wraps(func)
    def inner_close(self, *arg, **kwargs) -> bool:
        """Close the channel.

        :param args: positional arguments
        :param kwargs: named arguments

        :return: True if everything was successful otherwise False
        """
        log.internal_info(f"Close {self.channel.__class__.__name__} channel {self.channel.name!r}")
        try:
            ret = func(self, *arg, **kwargs)
            self.channel.close()
            return ret
        except Exception:
            log.exception(
                f"Unable to close  {self.channel.__class__.__name__}  channel communication {self.channel.name!r}"
            )
            return False

    return inner_close


def flash_target(func: Callable) -> Callable:
    """Flash firmware on the target, using associated auxiliary's
    flasher channel.

    :param func: decorated method

    :return: inner decorated function
    """

    @functools.wraps(func)
    def inner_flash(self, *arg, **kwargs) -> bool:
        """Flash the device under test.

        :param args: positional arguments
        :param kwargs: named arguments

        :return: True if everything was successful otherwise False
        """
        if self.flash is None and not self.is_instance:
            log.internal_debug("No flasher configured!")
            return func(self, *arg, **kwargs)

        try:
            log.internal_info("Flash target")
            with self.flash as flasher:
                flasher.flash()
            return func(self, *arg, **kwargs)
        except Exception:
            log.exception("Error occurred during flashing")
            return False

    return inner_flash
