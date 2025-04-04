
.. _xray:

Export results to Xray
======================

The ``xray`` CLI utility takes your Pykiso JSON test results report and export them on `Xray <https://xray.cloud.getxray.app/>`__.

Upload your results
-------------------
To upload your results to Xray users have to follow the command :

.. code:: bash

    xray --user USER_ID --password MY_API_KEY --url "https://xray.cloud.getxray.app/" upload --path-results-junit "./junit_files" --path-results-pickle "./pickle_files"


Options:
  --user TEXT                Xray user id [required]
  --password TEXT            Valid Xray API key (if not given ask at command prompt level)  [optional]
  --url TEXT                 URL of Xray server  [required]

  upload                     Upload the test results to Xray REST API endpoint [required]
  --test-execution-id        Test execution ID where to upload the test results [optional]
  --path-results-junit       Path to the junit files containing the test results reports [optional]
  --path-results-pickle      Path to the pickle files containing the test results reports [optional]
  --project-key              Project key [optional]
  --test-execution-name      To rename the test execution ticket [optional]
  --merge-xml-files          To merge several junit xml files [optional]
  --import-description       To import the test description as the xray test ticket description [optional]

  --help                        Show this message and exit.


The above command will create a new test execution ticket on Xray side or overwrite an existing one with the test results.

.. code:: python

  @pykiso.define_test_parameters(suite_id=1, case_id=1, aux_list=[aux1])
  class MyTest1(pykiso.RemoteTest):
      @parameterized.expand([("dummy_1"), ("dunny_1")])
      @pykiso.xray(test_key="ABC-123")
      def test_1(self, name):
          """Test run 1: parameterized test to check the assert true"""
          self.assertTrue(name.startswith("dummy"), f"{name} should start with dummy")


  @pykiso.define_test_parameters(suite_id=1, case_id=2, aux_list=[aux2])
  class MyTest2(pykiso.RemoteTest):
      @pykiso.xray(test_key="ABC-456")
      def test_2(self):
          """Test run 2: not parametrized test"""
          is_true = False
          print(f"is_true= {is_true}")
          self.assertTrue(is_true, f"{is_true} should be True")

      def tearDown(self):
          super().tearDown()
