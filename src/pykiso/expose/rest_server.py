##########################################################################
# Copyright (c) 2024-2024 Accenture GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
REST API Endpoint
*****************

:module: rest_server

:synopsis: Expose pykiso setup as a rest server

.. currentmodule:: rest_server
"""
from typing import Callable

import uvicorn
from fastapi import FastAPI

from pykiso.auxiliary import AuxiliaryInterface
from pykiso.endpoint import Endpoint


class RestServer(Endpoint):
    """Class to expose pykiso setup as a REST server."""

    def __init__(self, host: str, port: int):
        """Constructor

        :param host: host ip address
        :param port: host port

        """
        self.app = FastAPI(title="Pykiso REST Server")
        self.host = host
        self.port = port
        self.list_of_auxiliaries = []
        super().__init__()

    def expose_one_auxiliary(self, alias: str, auxiliary: AuxiliaryInterface):
        """Implements the parent method to expose one auxiliary.

        :param alias: Given auxiliary name from the yaml file
        :param auxiliary: The auxiliary instance associated with the alias

        """
        # Add to list of auxiliaries
        self.list_of_auxiliaries.append(alias)
        for method in dir(auxiliary):
            if (
                method.startswith("_")
                or not isinstance(getattr(auxiliary, method), Callable)
                or method == "get_instance"
                or "proxy" in method
                or "run_command" == method
                or method == "collect_messages"
            ):
                continue

            def bindFunction(name):
                return self.app.post("/" + alias + "/" + method)(getattr(auxiliary, name))

            bindFunction(method)

    def wait_for_termination(self):
        """Start of the REST server"""

        @self.app.get("/")
        async def root():
            return {"message": "Welcome to Pykiso", "auxiliaries": self.list_of_auxiliaries}

        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
        )
