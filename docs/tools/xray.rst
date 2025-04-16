
.. _xray:

Export results to Xray
======================

The ``xray`` CLI utility takes your Pykiso Junit test results report and export them on `Xray <https://xray.cloud.getxray.app/>`__.

Upload your results
-------------------
To upload your results to Xray users have to follow the command :

.. code:: bash

    xray --user USER_ID --password MY_API_KEY --url "https://xray.cloud.getxray.app/" upload --path-results path/reports/folder --test-execution-id

Options:
  --user TEXT                   Xray user id  [required]
  --password TEXT               Valid Xray API key (if not given ask at command prompt
                                level)  [optional]
  --url TEXT                    URL of Xray server  [required]
  --path-results PATH           Full path to the folder containing the JUNIT reports
                                [required]
  --test-execution-id TEXT      Xray test execution ticket id's use to import the
                                test results [optional][default value: None]
  --test-execution-name TEXT    Xray test execution name that will be created [optional][default value: None]
  --merge-xml-files             Merge all the xml files to be send in one xml file
  --import-description          Import the test function description as the xray ticket description
  --help                        Show this message and exit.


The above command will create a new test execution ticket on Xray side or overwrite an existing one with the test results.

Tests without parameterized:

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

For this test on Xray, 4 test execution tickets will be created, one per test cases.
