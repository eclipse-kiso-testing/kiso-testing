
.. _xray:

Export results to Xray
======================

The ``xray`` CLI utility takes your Pykiso JSON test results report and export them on `Xray <https://xray.cloud.getxray.app/>`__.

Upload your results
-------------------
To upload your results to Xray users have to follow the command :

.. code:: bash

    --xray-upload CLIENT_ID CLIENT_SECRET XRAY_API_BASE_URL

Options:
  CLIENT_ID TEXT                Xray user id  [required]
  CLIENT_SECRET TEXT            Valid Xray API key [required]
  XRAY_API_BASE_URL TEXT        URL of Xray server  [required]

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
