
.. _xray:

Export results to Xray
======================

The ``xray`` CLI utility takes your Pykiso Junit report and export them on `Xray <https://xray.cloud.getxray.app/>`__.

Upload your results
-------------------
To upload your results to Xray users have to follow the command :

.. code:: bash

    xray --user USER_ID --password MY_API_KEY --url https://xray.cloud.getxray.app/ upload  --path-results path/to/reports/folder --test-execution-id "BDU3-12345"
    --project-key KEY

Options:
  --user TEXT                   Xray user id  [required]
  --password TEXT               Valid Xray API key (if not given ask at command prompt
                                level)  [optional]
  --url TEXT                    URL of Xray server  [required]
  --project-key TEXT            Key of the project  [required]
  --path-results PATH           Full path to the folder containing the JUNIT reports
                                [required]
  --test-execution-id TEXT      Xray test execution ticket id's use to import the
                                test results [optional][default value: None]
  --test-execution-name TEXT    Xray test execution name that will be created [optional][default value: None]
  --merge-xml-files             Merge all the xml files to be send in one xml file
  --import-description          Import the test function description as the xray ticket description
  --help                        Show this message and exit.


The above command will create a new test execution ticket on Xray side or overwrite an existing one with the test results.
