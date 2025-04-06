from pathlib import Path

import pytest

import pykiso
from pykiso.endpoint import Endpoint


class EmptyServer(Endpoint):
    pass

class PartialServer(Endpoint):
    def expose_one_auxiliary(self, alias, auxiliary):
        pass

def test_endpoint_not_implemented():
    pykiso.load_config(Path(__file__).parent.resolve() / "dummy_serial.yaml")
    with pytest.raises(NotImplementedError):
        EmptyServer()
    with pytest.raises(NotImplementedError):
        PartialServer()
    pykiso.ConfigRegistry.delete_aux_con()

    # This test will be extended when additional implementation for expose_pykiso will exist
