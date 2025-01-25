.. _pykiso_exposed:

Pykiso as an Exposed Interface
------------------------------

Introduction
~~~~~~~~~~~~

Pykiso is more than just a testing framework — it's a structured interface for hardware interaction that can be reused and integrated
into other test runners and systems.
By decoupling the testing setup from the testing framework, Pykiso offers a powerful and reusable foundation for a wide range of embedded testing needs.

Why use Pykiso as an exposed interface?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Embedded systems often rely on tightly coupled, project-specific setups that are difficult to scale,
reuse, or integrate with other tools.
Pykiso changes that by offering a consistent, structured way to define and interact with hardware setups — independently of the testing framework you choose.

Whether you prefer writing tests with pytest, Unity-unittests zephyr-test-framework, or even triggering tests remotely via custom scripts or CI pipelines,
Pykiso can expose the hardware interface in a clean and standardized way.

.. warning::
    The exposed interface is still experimental and may not be functioning with all auxiliaries. E.g. one CAN auxiliary method returns a python object.

    In addition, currently only the auxiliaries are exposed. In the future, it will be possible to expose pykiso core APIs also via these interfaces.


Example
~~~~~~~

Definition of the test environment:

.. literalinclude:: ../../examples/next_pykiso2/pykiso_setup_expose/serial.yaml
    :language: yaml

Creation of the test script:

.. literalinclude:: ../../examples/next_pykiso2/pykiso_setup_expose/rest_endpoint.py
    :language: python
