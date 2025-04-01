.. _pykiso_as_simulator:

Pykiso as a simulator
---------------------

Introduction
~~~~~~~~~~~~

Pykiso consists of two main components:

* The testing framework
* The test environment creation and management

Together, these components enable embedded software engineers to efficiently test their software in a familiar manner.
Pykiso's testing framework adopts an approach similar to popular embedded testing frameworks,
such as Google Test, making it intuitive for engineers with experience in embedded systems.

Over the years, we have identified two main groups of Pykiso users:

* Those who embrace our opinionated approach to testing embedded software.
* Those who appreciate the core principles and resources but prefer a different approach to testing.

By decoupling the testing framework from the test environment creation,
Pykiso now caters to both groups, offering flexibility while retaining the benefits of its robust structure.



Workflow Overview
~~~~~~~~~~~~~~~~~

**Create a test environment**
Begin by defining your test environment in a configuration file. (Refer to :ref:`basic_config_file` for more details.)

**Strip the test suites section**
If needed, you can remove the `Test Suites` section from the configuration file to simplify the setup.

**Write your (test) script**
Create a Python script, import the Pykiso library, import the test environment and use the auxiliaries to interact with the system under test.


This workflow allows users to leverage Pykiso's testing capabilities while maintaining flexibility in how they define and manage their test environments.



Example
~~~~~~~

Definition of the test environment:

.. literalinclude:: ../../examples/next_pykiso2/pykiso_as_simulator/serial.yaml
    :language: yaml

Creation of the test script:

.. literalinclude:: ../../examples/next_pykiso2/pykiso_as_simulator/serial_simulation.py
    :language: python
