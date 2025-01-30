##########################################################################
# Copyright (c) 2010-2025 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Profiling
*********

:module: profiling

:synopsis: add helper functions for profiling

.. currentmodule:: profiling

"""

import json
from pathlib import Path

from viztracer import VizTracer
from viztracer.vcompressor import VCompressor


def profile(filename: str = "", compress: bool = False):
    """
    Decorator for VizTracer

    :param filename: the name of the file to save the result (default: module_name_function_name.json)
    :param compress: compress the result file if True and save it with .cvf extension (default: False)
    """

    def decorator(func: callable):
        result_filename = func.__module__ + "_" + func.__name__ + ".json" if filename == "" else filename

        def wrapper(*args, **kwargs):
            with VizTracer() as tracer:
                result = func(*args, **kwargs)
            if result_filename:
                tracer.save(result_filename)
            if compress:
                compressor = VCompressor()
                input_filename = Path(result_filename)
                output_filename = input_filename.with_suffix(".cvf").as_posix()
                with open(result_filename) as f:
                    data = json.load(f)
                    compressor.compress(data, output_filename)
                input_filename.unlink()  # delete the original file
            return result

        return wrapper

    return decorator
