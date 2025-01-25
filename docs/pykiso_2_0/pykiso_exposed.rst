.. _pykiso_exposed:

Pykiso With Exposed Interface
-----------------------------

Introduction
~~~~~~~~~~~~

On the journey of transforming pykiso to a full fledged test participant, its interface needs to be exposed and accessible by third party test runner.
This is a experimental feature (as of today) that allow to access the `auxiliaries` via an exposed interface.

The first provided interface would be REST based. The concept enable contributors to create and add their own "exposed" interface to pykiso.


Example
~~~~~~~

Definition of the test environment:

.. literalinclude:: ../../examples/next_pykiso2/pykiso_setup_expose/serial.yaml
    :language: yaml

Creation of the test script:

.. literalinclude:: ../../examples/next_pykiso2/pykiso_setup_expose/rest_endpoint.py
    :language: python
