Version ongoing
---------------

Channel auto-open
^^^^^^^^^^^^^^^^^

Add auto-open option for channels.
If used, this option open the channel after the auxiliary auto-start.


PCAN Connector
^^^^^^^^^^^^^^

By default the CCPCanCan will use the trace size define in during the initialisation.

The log path is now initialise if set at None.


Results can be exported to Xray
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

see :ref:`xray`

pykiso modules detachment
^^^^^^^^^^^^^^^^^^^^^^^^^

The pykiso modules are now detached from the main testing framework.
This enable users to define their hw setup and load it in python. The auxiliaries
can now be used in a more flexible way in python.
See :ref:`pykiso_as_simulator` for more details.

pykiso modules exposition
^^^^^^^^^^^^^^^^^^^^^^^^^

The pykiso modules can now be exposed via interfaces.
The first implemented interface is REST based.
This is an experimental feature.
See :ref:`pykiso_exposed` for more details.
