##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Loopback CChannel
*********************

:module: cc_raw_loopback

:synopsis: Loopback CChannel for testing purposes.

.. currentmodule:: cc_raw_loopback

"""
import threading
import time
from collections import deque
from typing import Dict, Optional

from pykiso import CChannel
from pykiso.types import MsgType


class CCLoopback(CChannel):
    """Loopback CChannel for testing purposes.

    Whatever gets sent via cc_send will land in a FIFO and can be received
    via cc_receive.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._loopback_buffer = None
        self.lock = threading.Lock()

    def _cc_open(self) -> None:
        """Open loopback channel."""
        self._loopback_buffer = deque()

    def _cc_close(self) -> None:
        """Close loopback channel."""
        self._loopback_buffer = None

    def _cc_send(self, msg: MsgType, **kwargs) -> None:
        """Send a message by simply putting message in deque.

        :param msg: message to send, should be Message type or bytes.
        """
        with self.lock:
            self._loopback_buffer.append(msg)

    def _cc_receive(self, timeout: float) -> Dict[str, Optional[bytes]]:
        """Read message by simply removing an element from the left side of deque.

        :param timeout: timeout applied on receive event

        :return: dictionary containing the received bytes if successful, otherwise None
        """
        with self.lock:
            # Simulate a blocking on receive
            start = time.time_ns()
            while (time.time_ns() - start) < timeout * 1e9:
                try:
                    recv_msg = self._loopback_buffer.popleft()
                    return {"msg": recv_msg}
                except IndexError:
                    time.sleep(0.1)
            return {"msg": None}
