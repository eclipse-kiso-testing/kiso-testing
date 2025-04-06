from pathlib import Path

import pykiso
from pykiso.expose import RestServer

# Load the configuration
pykiso.load_config(Path(__file__).parent.resolve() / "serial.yaml")

if __name__ == "__main__":
    # Start the REST server
    RestServer("0.0.0.0", 8000)
