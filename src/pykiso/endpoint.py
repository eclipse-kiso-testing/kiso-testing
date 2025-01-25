##########################################################################
# Copyright (c) 2024-2024 Accenture GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Endpoint Management
*******************

:module: endpoint

:synopsis: Expose pykiso setup as a server

.. currentmodule:: endpoint

"""

import logging

log = logging.getLogger(__name__)

from .auxiliary import AuxiliaryInterface
from .test_setup.config_registry import ConfigRegistry


class Endpoint:
    """Parent class to use for exposing pykiso setup as a server."""

    def __init__(self):
        # Get the list of auxiliaries
        self.auxiliaries: dict[str, AuxiliaryInterface] = ConfigRegistry.get_all_auxes()
        # Expose each auxiliary
        for alias, auxiliary in self.auxiliaries.items():
            self.expose_one_auxiliary(alias, auxiliary)
        # Expose pytkiso common interface
        self.expose_pykiso()
        # Wait for completion or termination
        self.wait_for_termination()

    def expose_one_auxiliary(self, alias: str, auxiliary: AuxiliaryInterface):
        """Method that will be called to expose one auxiliary.

        :param alias: Given name to the auxiliary in the yaml file
        :param auxiliary: auxiliary instance associated with the alias

        :raises NotImplementedError: This method should be implemented in the child class
        """
        raise NotImplementedError

    def expose_pykiso(self):
        """Method that will be called to expose the pykiso common interface.

        .. warning::
            This method will be implemented in the future.
        """
        pass

    def wait_for_termination(self):
        """Blocking method that will wait for the termination of the server.

        :raises NotImplementedError: This method should be implemented in the child class
        """
        raise NotImplementedError
