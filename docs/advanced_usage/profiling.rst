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

Example Usage
-------------

```python
from pykiso.profiling import profile

@profile
def test_method():
    pass

@profile
def test_method("result.json"):
    pass


@profile(compress=True)
def test_method():
    pass
```

Visualizing Profiling Results
=============================

To analyze the generated result file, use the `vizviewer` command-line tool. This tool launches a web server and opens a browser to provide an interactive visualization of your profiling data.

Running `vizviewer`
-------------------

```bash
vizviewer <result_filename>
```

Benefits of Profiling
=====================

✅ Identify performance bottlenecks
✅ Optimize test execution times
✅ Gain insights through interactive visualization

Start profiling today and take control of your test performance!
