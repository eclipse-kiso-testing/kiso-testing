
.. _xray:

Export results to Xray
======================

The ``xray`` CLI utility takes your Pykiso Junit test results report and export them on `Xray <https://xray.cloud.getxray.app/>`__.

Upload your results
-------------------

Upload the test results to an existing Xray test execution ticket
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To upload test results to an existing Xray test execution ticket, specify your Xray user ID, API key, server URL, and the path to the folder containing the JUNIT reports.
You must provide the **test execution ticket key** to overwrite the results in a specific ticket.


.. code:: bash

    xray --user USER_ID --password MY_API_KEY --url "https://xray.cloud.getxray.app/" upload --path-results path/reports/folder --test-execution-key "ABC-123"

Options:
  --user TEXT                         Xray user id  [required]
  --password TEXT                     Valid Xray API key (if not given ask at command prompt
                                      level)  [optional]
  --url TEXT                          URL of Xray server  [required]
  --path-results PATH                 Full path to the folder containing the JUNIT reports
                                      [required]
  --test-execution-key TEXT           Xray test execution ticket key's use to overwrite the
                                      test results (e.g ABC-123) [optional][default value: None]
  --test-execution-summary TEXT       Set or update the summary (Jira ticket title) of the Xray test execution ticket
                                      [optional][default value: None] Required when creating a new test execution ticket;
                                      optional when updating an existing one.
  --test-execution-description TEXT   Set or update the description (Jira ticket title) of the Xray test execution ticket
                                      [optional][default value: None] Required when creating a new test execution ticket;
                                      optional when updating an existing one.
  --merge-xml-files                   Merge all the xml files to be send in one xml file
  --not-append-test-results, -na      Do not append new test keys from the .xml(s) to the updated test execution,
                                      only overwrite already existing ones
  --help                              Show this message and exit.



Upload the test results on a new Xray test execution ticket
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When creating a new test execution ticket, you must also specify the test execution **summary** and **description**.


.. code:: bash

    xray --user USER_ID --password MY_API_KEY --url "https://xray.cloud.getxray.app/" upload --path-results path/reports/folder --test-execution-summary "My test execution summary" --test-execution-description "My test execution description"

Change the summary of the Xray test execution ticket
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can rewrite the test execution summary (the title on Jira ticket):

.. code:: bash

    xray --user USER_ID --password MY_API_KEY --url "https://xray.cloud.getxray.app/" upload --path-results path/reports/folder --test-execution-key "ABC-123" --test-execution-summary "New test execution summary"

Change the description of the Xray test execution ticket
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can rewrite the test execution description:

.. code:: bash

    xray --user USER_ID --password MY_API_KEY --url "https://xray.cloud.getxray.app/" upload --path-results path/reports/folder --test-execution-key "ABC-123" --test-execution-description "New test execution description"


Update existing test results only (do not append new tests)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, when uploading test results to an existing test execution ticket, new test results from the XML files are appended to the test execution.
If you want to only update the results of tests that already exist in the test execution ticket (without adding new tests), use the ``--not-append-test-results`` flag:

.. code:: bash

    xray --user USER_ID --password MY_API_KEY --url "https://xray.cloud.getxray.app/" upload --path-results path/reports/folder --test-execution-key "ABC-123" --not-append-test-results

This is useful when you want to:

- Update only specific test results without changing the test execution scope
- Maintain a fixed set of tests in your test execution ticket
- Prevent accidental addition of new tests to an existing test execution


Add the Xray decorator to the test functions
--------------------------------------------

To link your test cases with Xray, you need to add the ``@pykiso.xray(test_key="KEY")`` decorator to your test functions.
The ``test_key`` parameter should be the unique identifier of the test case in Xray.

Tests w/o parameterized
-----------------------

Tests without parameterized
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

  @pykiso.define_test_parameters(suite_id=1, case_id=1, aux_list=[aux1])
  class MyTest0(pykiso.RemoteTest):
      @pykiso.xray(test_key="ABC-123")
      def test_0(self, name):
          """Test run 1: parameterized test to check the assert true"""
          is_true = True
          self.assertTrue(is_true, f"{is_true} should start be True")


For this test on Xray, 1 test execution tickets will be created, for all the test cases.

Tests with parametrized:
~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

  @pykiso.define_test_parameters(suite_id=1, case_id=1, aux_list=[aux1])
  class MyTest1(pykiso.RemoteTest):
      @parameterized.expand([("dummy_1"), ("dunny_1")])
      @pykiso.xray(test_key="ABC-456")
      def test_1(self, name):
          """Test run 1: parameterized test to check the assert true"""
          self.assertTrue(name.startswith("dummy"), f"{name} should start with dummy")


  @pykiso.define_test_parameters(suite_id=1, case_id=2, aux_list=[aux2])
  class MyTest2(pykiso.RemoteTest):
      @pykiso.xray(test_key="ABC-789")
      def test_2(self):
          """Test run 2: not parametrized test"""
          is_true = False
          print(f"is_true= {is_true}")
          self.assertTrue(is_true, f"{is_true} should be True")

      def tearDown(self):
          super().tearDown()

For this test on Xray, 1 test execution ticket will be created.
In the comment column, the test results for each test case will be displayed.
