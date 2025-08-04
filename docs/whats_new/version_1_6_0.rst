Version 1.6.0
-------------

Better return type when sending UDS messages
^^^^^^^^^^^^^^^^^

New method `UdsAuxiliary.send_uds`, available in two versions (`typing.overload`):
- when expecting a response (`response_required=True`) from remote component, returns the response,
or fails with an exception
- otherwise, return `None`, or fail with an exception

This is more in line with what exising clients expected.

The previous version of this method, `UdsAuxiliary.send_uds_raw`, has been kept with the same API,
for backwards compatibility: return `False` on error, unless the error is because no response
was received while one was expected, in which case a `ReponseNotReceivedException` is raised.


See :ref:`uds_server_auxiliary`
