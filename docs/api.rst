.. _api:

API Documentation
=================

Test Cases
----------

.. automodule:: pykiso.test_coordinator.test_case
    :members:

Exposed Interface
-----------------

`pykiso` comes with some ready to use exposed interfaces.

.. toctree::
    :maxdepth: 3
    :titlesonly:

    expose/index


Connectors
----------

`pykiso` comes with some ready to use implementations of different connectors.

.. toctree::
    :maxdepth: 3
    :titlesonly:

    connectors/CChannels/index
    connectors/Flashers/index

Auxiliaries
-----------

.. toctree::
    :maxdepth: 3
    :titlesonly:

    auxiliary_interfaces/index.rst
    auxiliaries/index.rst

Message Protocol
----------------

.. automodule:: pykiso.message
    :members:


Import Magic
------------

.. automodule:: pykiso.test_setup.dynamic_loader
    :members:

.. automodule:: pykiso.test_setup.config_registry
    :members:

Test Suites
-----------

.. automodule:: pykiso.test_coordinator.test_suite
    :members:

Test Execution
--------------
.. automodule:: pykiso.test_coordinator.test_execution
    :members:

Test-Message Handling
---------------------

.. automodule:: pykiso.test_coordinator.test_message_handler
    :members:

Test Results
------------

.. automodule:: pykiso.test_result.xml_result
    :members:

.. automodule:: pykiso.test_result.text_result
    :members:

.. automodule:: pykiso.test_result.assert_step_report
    :members:
