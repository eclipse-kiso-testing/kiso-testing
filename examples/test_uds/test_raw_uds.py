##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
UDS auxiliary simple example
****************************

:module: test_raw_uds

:synopsis: Example test that shows how to use the uds auxiliary

.. currentmodule:: test_raw_uds

"""

import logging
import time
import unittest

from uds import IsoServices

import pykiso
from pykiso.auxiliaries import uds_aux


@pykiso.define_test_parameters(suite_id=1, case_id=1, aux_list=[uds_aux])
class ExampleUdsTest(pykiso.BasicTest):
    def setUp(self):
        """Hook method from unittest in order to execute code before test case run."""
        pass

    def test_run(self):
        logging.info(
            f"--------------- RUN: {self.test_suite_id}, {self.test_case_id} ---------------"
        )

        """
        Simply go in extended session.

        The equivalent command using an ODX file would be :

        extendedSession_req = {
            "service": IsoServices.DiagnosticSessionControl,
            "data": {"parameter": "Extended Diagnostic Session"},
        }
        diag_session_response = uds_aux.send_uds_config(extendedSession_req)
        """
        diag_session_response = uds_aux.send_uds_raw([0x10, 0x01])
        self.assertEqual(diag_session_response[:2], [0x50, 0x01])

    def tearDown(self):
        """Hook method from unittest in order to execute code after test case run."""
        pass
