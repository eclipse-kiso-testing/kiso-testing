##########################################################################
# Copyright (c) 2010-2022 Robert Bosch GmbH
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0.
#
# SPDX-License-Identifier: EPL-2.0
##########################################################################

"""
Acroname Control Auxiliary
**************************

:module: acroname_auxiliary

:synopsis: Auxiliary used to control acroname usb hubs.

.. currentmodule:: acroname_auxiliary

"""
import logging
from typing import Any, Optional

import brainstem
from brainstem.result import Result

from pykiso.auxiliary import AuxiliaryInterface
from pykiso.types import MsgType

log = logging.getLogger(__name__)

ERROR_MESSAGES = {
    0: "No Error occurred.",
    1: "Memory allocation/de-allocation error.",
    2: "Invalid parameters given.",
    3: "Entity, module or information not found.",
    4: "File name is to long.",
    5: "Module or resource is currently busy.",
    6: "An Input/Output error occurred.",
    7: "Invalid Mode or mode not accessible for current state.",
    8: "Write error occurred.",
    9: "Read error occurred.",
    10: "Unexpected end of file encountered.",
    11: "Resource not ready.",
    12: "Insufficient permissions.",
    13: "Request is outside of valid range.",
    14: "Size is incorrect for resource.",
    15: "Buffer was overrun or will be.",
    16: "Unable to parse command.",
    17: "Configuration is invalid.",
    18: "Timeout occurred.",
    19: "Could not initialize resource.",
    20: "Version mismatch",
    21: "Functionality unavailable or unimplemented.",
    22: "Duplicate request received.",
    23: "Request was canceled",
    24: "packet was invalid or had invalid contents.",
    25: "connection is no longer valid, or was closed.",
    26: "Requested entity does not exist.",
    27: "Command to short, not enough data to parse.",
    28: "Entity is not available, or does not exist.",
    29: "Option for given entity is invalid.",
    30: "Error allocating or acquiring a resource.",
    31: "Media not found or not available.",
    32: "Unknown error encountered.",
}


class AcronameAuxiliary(AuxiliaryInterface):
    """Auxiliary used to control acroname usb hubs"""

    MICROVOLT_TO_UNIT = {"uV": 1, "mV": 1e-3, "V": 1e-6}
    MICROAMP_TO_UNIT = {"uA": 1, "mA": 1e-3, "A": 1e-6}

    def __init__(self, serial_number: str | int = 0, **kwargs):
        """Constructor

        :param serial_number: serial number to connect to as hex string. Example "0x66F4859B"
        """
        super().__init__(
            is_proxy_capable=False,
            tx_task_on=False,
            rx_task_on=False,
            connector_required=False,
            **kwargs,
        )

        self.serial_number = int(serial_number, 16) if isinstance(serial_number, str) else serial_number
        self.stem = brainstem.stem.USBHub2x4()

    def _create_auxiliary_instance(self) -> bool:
        """Open the connector. Stop auxiliary if not possible.

        :return: True if successful
        """

        log.internal_info("Create auxiliary instance")

        result = self.stem.discoverAndConnect(brainstem.link.Spec.USB, self.serial_number)
        if result == (Result.NO_ERROR):
            result = self.stem.system.getSerialNumber()
            log.internal_info("Connected to USBStem with serial number: 0x%08X" % result.value)
        else:
            log.error("Could not connect to usb hub acroname")
            self.eval_result(result)
            return False

        return True

    def _delete_auxiliary_instance(self) -> bool:
        """Close the connector.

        :return: always True
        """
        log.internal_info("Delete auxiliary instance")
        try:
            self.stem.disconnect()
        except Exception:
            log.exception("Unable to close usb hub acroname.")
        return True

    @staticmethod
    def eval_result(result: Result) -> None:
        """Log error message if exist from acroname Result object.
        :param result: result code to evaluate
        """
        if result != (Result.NO_ERROR):
            log.error(f"Error occurred: {ERROR_MESSAGES[result]}")

    def set_port_enable(self, port: int) -> int:
        """Enable power and data lines for a USB port.

        :param port: the USB port number
        :return: brainstem error code. 0 if no error.
        """
        result = self.stem.usb.setPortEnable(port)
        self.eval_result(result)
        return result

    def set_port_disable(self, port: int) -> int:
        """Disable power and data lines for a USB port.

        :param port: the USB port number
        :return: brainstem error code. 0 if no error.
        """
        result = self.stem.usb.setPortDisable(port)
        self.eval_result(result)
        return result

    def get_port_current(self, port: int, unit: str = "A") -> Optional[float]:
        """Get the current through the power line for selected usb port.

        :param port: the USB port number
        :param unit: unit of the result in "uA", "mA" or "A". Default "A"
        :return: port current for given unit. None if unit is not supported.
        """
        port_current_ua = self.stem.usb.getPortCurrent(port)
        self.eval_result(port_current_ua.error)
        try:
            port_current = port_current_ua.value * self.MICROAMP_TO_UNIT[unit]

        except KeyError:
            log.error(f"Unit '{unit}' is not supported. Current value will be set to None.")
            return None

        return port_current

    def get_port_voltage(self, port: int, unit: str = "V") -> Optional[float]:
        """Get the voltage of the selected usb port.

        :param port: the USB port number
        :param unit: unit of the result in "uV", "mV" or "V". Default "V"
        :return: port voltage for given unit. None if unit is not supported.
        """
        port_voltage_uv = self.stem.usb.getPortVoltage(port)
        self.eval_result(port_voltage_uv.error)
        try:
            port_voltage = port_voltage_uv.value * self.MICROVOLT_TO_UNIT[unit]

        except KeyError:
            log.error(f"Unit '{unit}' is not supported. Voltage value will be set to None.")
            return None

        return port_voltage

    def get_port_current_limit(self, port: int, unit: str = "A") -> Optional[float]:
        """Get the current limit for the port.

        :param port: the USB port number
        :param unit: unit of the result in "uA", "mA" or "A". Default "A"
        :return: port current limit for given unit. None if unit is not supported.
        """
        result = self.stem.usb.getPortCurrentLimit(port)
        self.eval_result(result.error)
        try:
            port_current_limit = result.value * self.MICROAMP_TO_UNIT[unit]
        except KeyError:
            log.error(f"Unit '{unit}' is not supported. Port current value will be set to None.")
            return None

        return port_current_limit

    def set_port_current_limit(self, port: int, amps: float, unit: str = "A") -> int:
        """Set the current limit for the port. If the set limit is not achievable,
        devices will round down to the nearest available current limit setting.

        :param port: the USB port number
        :param amps: value for port current to set in "uA", "mA" or "A". Default "A"
        :param unit: unit for the value to set. Default Ampere
        :return: brainstem error code. 0 if no error.
        """
        try:
            micro_volt_value = int(amps / self.MICROAMP_TO_UNIT[unit])
        except KeyError:
            log.error(f"Unit '{unit}' is not supported. Port value won't be changed")
            return

        result = self.stem.usb.setPortCurrentLimit(port, micro_volt_value)
        self.eval_result(result)
        return result

    def _run_command(self, cmd_message: Any, cmd_data: Optional[bytes]) -> None:
        """Not used.

        Simply respect the interface.
        """

    def _receive_message(self, timeout_in_s: float) -> None:
        """Not used.

        Simply respect the interface.
        """
