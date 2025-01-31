Profiling
*********

Overview
========

Profiling your test methods helps you analyze performance and optimize efficiency.
The `@profile` decorator makes it easy to profile your test methods and automatically
generates a result file based on the test module name and test name if no file path is provided.

Using the `@profile` Decorator
==============================

The `@profile` decorator can be used in two ways:
- **Default usage**: Generates an uncompressed result file named after the test module and test name in your current working directory.
- **Specifying** a file path**: Generates an uncompressed result file with the specified file path.
- **Compressed output**: When `compress=True` is set, the output file is compressed into a `.cvf` format.

Decorator Example
-----------------

.. code:: python

    from pykiso.profiling import profile

    @profile
    def test_method():
        pass

    @profile("result.json")
    def test_method():
        pass


    @profile(compress=True)
    def test_method():
        pass


Using the `profile_manager`
===========================

If you want to profile a section of your code, you can use the `profile_manager` context manager.
In this case, you need to specify the file path and whether to compress the output file.
Everything inside the context manager will be profiled.

Context Manager Example
-----------------------

.. code:: python

    from pykiso.profiling import profile_manager

    def test_method():
        with profile_manager("testrun2.json", compress=False):
            time.sleep(1)

Using the get_tracer() function
===============================

If you want to be in full control of the profiling process, you can use the `get_tracer()` function.
It will return the viztracer.Tracer object, which you can use to start and stop the profiling process.
To create a result file, you need to call the save() method on the Tracer object.

Raw Viztracer Example
---------------------

.. code:: python

    from pykiso.profiling import get_tracer

    def test_method():
        tracer = get_tracer()
        tracer.start()
        time.sleep(1)
        tracer.stop()
        tracer.save("testrun3.json")


Visualizing Profiling Results
=============================

To analyze the generated result file, use the `vizviewer` command-line tool. This tool launches a web server and opens a browser to provide an interactive visualization of your profiling data.

Running `vizviewer`
-------------------

.. code:: bash

    vizviewer <result_filename>.json


Benefits of Profiling
=====================

✅ Identify performance bottlenecks
✅ Optimize test execution times
✅ Gain insights through interactive visualization

Start profiling today and take control of your test performance!

.. note::
    For more information on the `viztracer` tool, refer to the `viztracer documentation <https://viztracer.readthedocs.io/en/latest/>`_.
