Version 1.3.0
-------------

Upload test results from xml files to xray API with simple CLI
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is now possible to export the test results contained in a JUNIT xml file to Xray API
with a simple CLI.

To link the test cases with Xray, the `@pykiso.xray(test_key="KEY")` decorator must be added
above the test function.

* First, run the decorated tests with the option to generate the JUNIT xml file.
* Second, upload the test results to a single Xray test execution ticket with the xray CLI.

If a `--test-execution-key` is specified, the test results will overwrite the existing ticket.
If not, a new test execution ticket will be created and will contain the test results.

This CLI supports parameterized and not parameterized tests.

see :ref:`xray`
