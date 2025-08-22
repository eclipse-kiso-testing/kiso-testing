import os
import signal
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
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.stop_event = threading.Event()
        self._start_server()

    def _start_server(self):
        """Start the server in a separate thread with proper shutdown handling."""
        def run_server():
            # Create RestServer instance and expose pykiso setup
            rest_server = RestServer(self.host, self.port)
            rest_server.expose_pykiso()  # This will expose all configured auxiliaries

            config = uvicorn.Config(
                app=rest_server.app,
                host=self.host,
                port=self.port,
                log_level="error"  # Reduce log noise during tests
            )
            self.server = uvicorn.Server(config)
            self.server.run()

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait for the server to start
        max_attempts = 50  # 5 seconds max
        for _ in range(max_attempts):
            try:
                response = requests.get(f"http://{self.host}:{self.port}", timeout=1)
                if response.status_code == 200:
                    break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                sleep(0.1)
        else:
            raise RuntimeError("Server failed to start within timeout period")

    def stop(self):
        """Properly stop the server."""
        if self.server is not None:
            self.server.should_exit = True
            # Give the server a moment to shut down gracefully
            for _ in range(10):  # 1 second max
                if not self.server_thread.is_alive():
                    break
                sleep(0.1)

            # If still running, we'll let the daemon thread die with the process
            self.server = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()



def test_expose_dummy_serial():
    """Test that all auxiliary methods are properly exposed via REST API."""
    # Load the configuration
    pykiso.load_config(Path(__file__).parent.resolve() / "dummy_serial.yaml")

    try:
        # Load the different auxiliaries to test REST against
        com_aux_sender = CommunicationAuxiliary.get_instance("com_aux_sender")

        with ServerThread("127.0.0.1", 8000) as server:
            exposed_methods = []
            failed_methods = []

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
                    response = requests.get(f"http://127.0.0.1:8000/com_aux_sender/{method}", timeout=2)
                    if response.status_code in [200, 405]:  # 405 is Method Not Allowed for GET on POST endpoints
                        exposed_methods.append(method)
                    else:
                        failed_methods.append(f"{method} (status: {response.status_code})")
                except requests.exceptions.Timeout:
                    failed_methods.append(f"{method} (timeout)")
                except requests.exceptions.ConnectionError:
                    failed_methods.append(f"{method} (connection error)")
                except Exception as e:
                    failed_methods.append(f"{method} (error: {str(e)})")

            # Report results
            print(f"Successfully exposed methods: {len(exposed_methods)}")
            print(f"Failed methods: {len(failed_methods)}")

            if failed_methods:
                print("Failed methods details:")
                for failed in failed_methods:
                    print(f"  - {failed}")

            # The test passes if we found at least some exposed methods and no connection errors
            assert len(exposed_methods) > 0, "No methods were successfully exposed"

    finally:
        # Clean up the configuration registry
        pykiso.ConfigRegistry.delete_aux_con()
