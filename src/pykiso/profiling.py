##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

import json
from pathlib import Path

from viztracer import VizTracer
from viztracer.vcompressor import VCompressor


# decorator for VizTracer
def profile(filename: str = "result.json", compress: bool = False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            with VizTracer() as tracer:
                result = func(*args, **kwargs)
            if filename:
                tracer.save(filename)
            if compress:
                compressor = VCompressor()
                input_filename = Path(filename)
                output_filename = input_filename.with_suffix(".cvf").as_posix()

                with open(filename) as f:
                    data = json.load(f)
                    compressor.compress(data, output_filename)
                input_filename.unlink()  # delete the original file
            return result

        return wrapper

    return decorator
