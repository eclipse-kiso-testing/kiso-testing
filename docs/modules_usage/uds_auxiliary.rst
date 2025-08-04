.. _uds_auxiliary_usage:

Using UDS protocol
==================

UdsAuxiliary class (:py:class:`pykiso.lib.auxiliaries.udsaux.uds_auxiliary.UdsAuxiliary`) contained
in uds_auxiliary.py is the main interface between user and all the behind implemented logic.
This class defines usable keywords(methods) for scripters in order to send uds requests to the device under test (raw or configurable)...

Configuration
-------------

To configure the UDS auxiliary 3 parameters are mandatory :

- odx_file_path: path to the odx formatted ecu diagnostic definition file.

.. note:: More information about yaml test configuration creation are available under Test Integration Framework project documentation.

Find below a complete configuration example :

.. code:: yaml

    auxiliaries:
      uds_aux:
        connectors:
            com: can_channel
        config:
          # you can specify your odx file by using odx_file_path parameter
          # and instead of using send_uds method use the send_uds_config
          # for a more human readable command
          odx_file_path: null
          request_id : 0x123
          response_id : 0x321
          # uds_layer parameter is not mandatory and by default the following
          # values will be applied:
          # transport_protocol -> CAN
          # p2_can_client -> 5
          # p2_can_server -> 1
          uds_layer:
            transport_protocol: 'CAN'
            # p2_can specifies receive time outs in seconds
            p2_can_client: 5
            p2_can_server: 1
          # tp_layer parameter is not mandatory and by default the following
          # values will be applied:
          # addressing_type -> NORMAL
          # n_sa -> 0xFF
          # n_ta -> 0xFF
          # n_ae -> 0xFF
          # m_type -> DIAGNOSTICS
          # discard_neg_resp -> False
          tp_layer:
            addressing_type: 'NORMAL'
            n_sa: 0xFF
            n_ta: 0xFF
            n_ae: 0xFF
            m_type: 'DIAGNOSTICS'
            discard_neg_resp: False
        type: pykiso.lib.auxiliaries.udsaux.uds_auxiliary:UdsAuxiliary
    connectors:
      can_channel:
        config:
          interface : 'pcan'
          channel: 'PCAN_USBBUS1'
          state: 'ACTIVE'
        type: pykiso.lib.connectors.cc_pcan_can:CCPCanCan
    test_suite_list:
    - suite_dir: test_uds
      test_filter_pattern: 'test_raw_uds*.py'
      test_suite_id: 1


Send UDS Raw Request
--------------------

Send UDS request as list of raw bytes.

The method send_uds(:py:meth:`pykiso.lib.auxiliaries.udsaux.UdsAuxiliary.send_uds`) takes one mandatory parameter msg_to_send and one optional : timeout_in_s
The parameter msg_to_send is simply the UDS request payload which is a list of bytes.

The method send_uds method returns a :py:class:`~ebplugins.udsaux.uds_response.UdsResponse` object, which is a subclass of `UserList
<https://docs.python.org/3/library/collections.html#collections.UserList>`_.
UserList allow to keep property of the list, meanwhile attributes can be set, for UdsResponse, defined attributes
refer to the positivity of the response, and its NRC if negative.

.. code:: python

    class UdsResponse(UserList):
        NEGATIVE_RESPONSE_SID = 0x7F

        def __init__(self, response_data) -> None:
            super().__init__(response_data)
            self.is_negative = False
            self.nrc = None
            if self.data and self.data[0] == self.NEGATIVE_RESPONSE_SID:
                self.is_negative = True
                self.nrc = NegativeResponseCode(self.data[2])

Here is an example:

.. code:: python

    import pykiso
    from pykiso.auxiliaries import uds_aux
    from collections import UserList

    @pykiso.define_test_parameters(suite_id=1, case_id=1, aux_list=[uds_aux])
    class ExampleUdsTest(pykiso.BasicTest):
        def setUp(self):
            """Hook method from unittest in order to execute code before test case run.
            """
            pass

        def test_run(self):
            # Set extended session
            diag_session_response = uds_aux.send_uds([0x10, 0x03])
            self.assertEqual(diag_session_response[:2], [0x50, 0x03])
            self.assertEqual(type(diag_session_response), UserList)
            self.assertFalse(diag_session_response.is_negative)

        def tearDown(self):
            """Hook method from unittest in order to execute code after test case run.
            """
            pass

Send UDS Config Request
-----------------------

Send UDS request as a configurable data dictionary. This method can be more practical for UDS requests with long payloads and a multitude of parameters.
The method send_uds_config(:py:meth:`pykiso.lib.auxiliaries.udsaux.uds_auxiliary.UdsAuxiliary.send_uds_config`) takes one mandatory parameter msg_to_send and an optional one timeout_in_s.
The parameter msg_to_send is the UDS request defined as a configurable dictionary that always respects the below defined template:

.. note:: this feature is only available if a valid ODX file is given at auxiliary configuration level

.. code:: python

    req = {
        'service': %SERVICE_ID%,
        'data': %DATA%
    }

SERVICE_ID -> SID (Service Identifier) of the UDS request either defined as a byte or the corresponding enum label:

.. code:: python

    class IsoServices(IntEnum):
        DiagnosticSessionControl = 0x10
        EcuReset = 0x11
        SecurityAccess = 0x27
        CommunicationControl = 0x28
        TesterPresent = 0x3E
        AccessTimingParameter = 0x83
        SecuredDataTransmission = 0x84
        ControlDTCSetting = 0x85
        ResponseOnEvent = 0x86
        LinkControl = 0x87
        ReadDataByIdentifier = 0x22
        ReadMemoryByAddress = 0x23
        ReadScalingDataByIdentifier = 0x24
        ReadDataByPeriodicIdentifier = 0x2A
        DynamicallyDefineDataIdentifier = 0x2C
        WriteDataByIdentifier = 0x2E
        WriteMemoryByAddress = 0x3D
        ClearDiagnosticInformation = 0x14
        ReadDTCInformation = 0x19
        InputOutputControlByIdentifier = 0x2F
        RoutineControl = 0x31
        RequestDownload = 0x34
        RequestUpload = 0x35
        TransferData = 0x36
        RequestTransferExit = 0x37


DATA -> dictionary that contains the following keys:
    - 'parameter': DID (Data Identifier) of the UDS request. (In most UDS services with DID)
    - %param_n%: one or many keys that represent the parameters related to the service, those depend on ODX definition that is tested.

See some examples of UDS requests below:

.. code:: python

    import pykiso
    from pykiso.auxiliaries import uds_aux
    from uds import IsoServices

    @pykiso.define_test_parameters(suite_id=1, case_id=1, aux_list=[uds_aux])
    class ExampleUdsTest(pykiso.BasicTest):
        def setUp(self):
            """Hook method from unittest in order to execute code before test case run.
            """
            pass

        def test_run(self):
	        extendedSession_req = {
	            "service": IsoServices.DiagnosticSessionControl,
	            "data": {"parameter": "Extended Diagnostic Session"},
	        }
	        diag_session_response = uds_aux.send_uds_config(extendedSession_req)

        def tearDown(self):
            """Hook method from unittest in order to execute code after test case run.
            """
            pass


The optional parameter timeout_in_s (by default fixed to 6 seconds) simply represents the maximum
amount of time in second to wait for a response from the device under test. If this timeout is reached, the
uds-auxiliary stops to acquire and log an error.

If the corresponding response is received from entity under test, send_uds_config method returns it also as a preconfigured dictionary.
In case of a UDS positive response and no data to be returned, None is returned by the send_uds_config method.
In case of a UDS negative response, a dictionary with the key 'NRC' is returned and the NRC value.
Optionally, 'NRC_Label' may be returned if it is defined in ODX for the called service, containing the uds negative response description.

UDS Reset functions
--------------------

Reset might be integrated in different tests.

The methods:

- soft_rest(:py:meth:`pykiso.lib.auxiliaries.udsaux.uds_auxiliary.UdsAuxiliary.soft_reset`)
- hard_reset(:py:meth:`pykiso.lib.auxiliaries.udsaux.uds_auxiliary.UdsAuxiliary.hard_reset`)
- force_ecu_reset(:py:meth:`udsaux.uds_auxiliary.UdsAuxiliary.force_ecu_reset`)

do not take any argument, and regarding the config (with our without odx file) will send either raw message, or
uds config (except for the key_off_on methods, but can remain acceptable for odx uds config)

.. code:: python

    Soft reset
    uds_aux.soft_reset()

UDS check functions
--------------------

Check functions might be integrated in different tests.

The methods:

- check_raw_response_negative(:py:meth:`pykiso.lib.auxiliaries.udsaux.uds_auxiliary.UdsAuxiliary.check_raw_response_negative`)
- check_raw_response_positive(:py:meth:`pykiso.lib.auxiliaries.udsaux.uds_auxiliary.UdsAuxiliary.check_raw_response_positive`)

The methods take as only mandatory argument the received response.
The parameter rest is the response as a userlist object.

.. code:: python

    #Check raw response is positive
    uds_aux.check_raw_response_positive(resp)

    #Check raw response is negative
    uds_aux.check_raw_response_negative(resp)

UDS read & write data
---------------------

Read data(:py:meth:`udsaux.uds_auxiliary.UdsAuxiliary.read_data`) and write(:py:meth:`udsaux.uds_auxiliary.UdsAuxiliary.write_data`)
are two helper API that use send_uds_config with specific ISO services (:py:meth:`udsaux.uds_utils.UdsAuxiliary.read_data`)

.. code:: python

    ReadDataByIdentifier = 0x22

    WriteDataByIdentifier = 0x2E

Using write_data takes two arguments : parameter, and value.
Parameter is simply a string that refer to the name of the data you want to modify, and value
is simply the value you want to assign to the chosen parameters
API must return None in case of positive response, and dictionary with NRC in it (for further information,
check in send_uds_config documentation).
Using this API is similar to do this :

.. code:: python

    req = {
        'service': IsoServices.WriteDataByIdentifier,
        'data': {'parameter': 'MyProduct', 'dataRecord': [('SuperProduct', '12345')]}
    }

    resp = uds_aux.send_uds_config(writeProductCode_req)
    return resp

In the same way, read_data takes one argument : parameter.

Parameter is a string that contain the name of the data that is to be read. API must return dictionary with either
data associated to the read parameter, or NRC.

.. _start_stop_tester_present_sender:

UDS tester present sender
-------------------------

In order for any diagnostic session to be kept open, a tester presence frame has to be sent every 5 seconds.
For this purpose, the tester present sender context manager can be used, it will send the tester
present frame at the period given, allowing you to keep the session open for more than 5 seconds.

.. code:: python

    # start sending tester present messages every 3 seconds until the context manager is exited
    with uds_aux.tester_present_sender(period=3):
        # Perform uds commands here

It is also possible to start and stop the tester present sender manually with the methods
start_tester_present_sender and stop_tester_present_sender.

.. code:: python

    # start sending tester present messages every 1 seconds until the context manager is exited
    uds_aux.start_tester_present_sender(period=1)
    # Perform uds commands here
    uds_aux.stop_tester_present_sender()

It is then possible to check if the tester present is active with the attribute is_tester_present

.. code:: python

    if uds_aux.is_tester_present:
        # Perform commands here
