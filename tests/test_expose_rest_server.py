import threading
from pathlib import Path
from time import sleep
from typing import Callable

import pytest
import requests
import uvicorn

import pykiso
from pykiso.expose.rest_server import RestServer
from pykiso.lib.auxiliaries.communication_auxiliary import CommunicationAuxiliary


# class to start and stop the server in a thread
class ServerThread:
    def __init__(self, host: str, port: int):
        self.server_thread = threading.Thread(target=RestServer, args=(host, port), daemon=True)
        self.server_thread.start()
        # Wait for the server to start
        while True:
            try:
                requests.get(f"http://{host}:{port}")
                break
            except requests.exceptions.ConnectionError:
                sleep(0.1)



    def stop(self):
        del uvicorn.server

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()



def test_expose_dummy_serial():
# Load the configuration
    pykiso.load_config(Path(__file__).parent.resolve() / "dummy_serial.yaml")
    # Load the different auxiliaries to test REST against
    com_aux_sender = CommunicationAuxiliary.get_instance("com_aux_sender")
    #com_aux_receiver = CommunicationAuxiliary.get_instance("com_aux_receiver")

    with ServerThread("0.0.0.0", 8000):
        for method in dir(com_aux_sender):
            # Skip private methods, non-callable methods, and methods that should not be exposed
            if (
                method.startswith("_")
                or not isinstance(getattr(com_aux_sender, method), Callable)
                or method == "get_instance"
                or "proxy" in method
                or "run_command" == method
                or method == "collect_messages"
            ):
                continue
            # Check if the method is exposed
            try:
                requests.get(f"http://0.0.0.0:8000/com_aux_sender/{method}")
            except requests.exceptions.ConnectionError:
                assert False, f"Method {method} is not exposed"

    pykiso.ConfigRegistry.delete_aux_con()
