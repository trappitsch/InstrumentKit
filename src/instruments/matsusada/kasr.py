#!/usr/bin/env python
"""
Driver for Matsusada KAS-R series high-voltage power supplies
via serial/TCP.
"""

from enum import Enum
from instruments.abstract_instruments import Instrument
from instruments.units import ureg as u
from instruments.util_fns import ProxyList

class KASR(Instrument):
    """
    Driver for Matsusada KAS-R HV power supplies.

    Provides properties and methods to:
      - Turn output on/off
      - Set/get target voltage (VSET)
      - Read actual output voltage (VGET) and current (IGET)
      - Set polarity (POL P / POL N)
      - Read status/error info (STS)
      - A purely software “current_limit” .
    """

    class Polarity(Enum):
        POSITIVE = "P"
        NEGATIVE = "N"

    def __init__(self, filelike):
        """
        :param filelike: The file-like connection (e.g. serial port or TCP socket)
        """
        super().__init__(filelike)

        self.terminator = "\r"  # or "\r\n"

    # --------------------------------------------------------
    # 1) ON / OFF
    # --------------------------------------------------------
    @property
    def output_enabled(self) -> bool:
        """
        Get or set whether the HV output is ON or OFF.
        Internally uses the “OUT?” query and “OUT ON/OFF” commands.
        """
        resp = self.query("OUT?")  # e.g. returns "OUT=OFF" or "OUT=ON"
        if "=ON" in resp:
            return True
        else:
            return False

    @output_enabled.setter
    def output_enabled(self, value: bool):
        if value:
            self.sendcmd("OUT ON")
        else:
            self.sendcmd("OUT OFF")

    # --------------------------------------------------------
    # 2) Voltage setpoint
    # --------------------------------------------------------
    @property
    def voltage_set(self) -> float:
        """
        The “set” voltage in kV, i.e. what was last commanded to the supply.
        Corresponds to “VSET?” query and “VSET x.xx” command.
        Units are kV in the Matsusada doc. We can store them as float (kV).
        """
        # "In response to 'VSET?', it returns the set voltage value like VSET=12.34"
        resp = self.query("VSET?")
        # parse e.g. "VSET=12.34"
        if "=" in resp:
            val_str = resp.split("=")[1]
            return float(val_str)
        return 0.0  # fallback if parse fails

    @voltage_set.setter
    def voltage_set(self, kv: float):
        """
        Set the desired output voltage (in kV).
        e.g. `voltage_set = 12.34` => send "VSET 12.34"
        """
        # Optionally clamp to allowable range:
        if kv < 0:
            kv = 0
        # send "VSET 12.34"
        self.sendcmd(f"VSET {kv:.2f}")

    # --------------------------------------------------------
    # 3) Actual measured voltage
    # --------------------------------------------------------
    @property
    def voltage_real(self) -> float:
        """
        The actual measured output voltage in kV (read by “VGET”).
        Example response: “VGET=12.34”
        """
        resp = self.query("VGET")
        # parse e.g. "VGET=12.34"
        if "=" in resp:
            val_str = resp.split("=")[1]
            return float(val_str)
        return 0.0

    # --------------------------------------------------------
    # 4) Actual measured current
    # --------------------------------------------------------
    @property
    def current_real(self) -> float:
        """
        The actual measured output current in mA (read by “IGET”).
        Example response: “IGET=0.12”
        """
        resp = self.query("IGET")
        # parse e.g. "IGET=0.12"
        if "=" in resp:
            val_str = resp.split("=")[1]
            return float(val_str)
        return 0.0

    # --------------------------------------------------------
    # 5) Polarity
    # --------------------------------------------------------
    @property
    def polarity(self) -> Polarity:
        """
        Get the supply polarity: "POL=P" or "POL=N".
        According to the doc, "POL?" should return "POL=P" or "POL=N".
        If the device doesn't support reversing polarity, it may return an error or a fixed string.
        """
        resp = self.query("POL?").strip()
        # e.g. we expect something like "POL=P" or "POL=N"
        if "=" not in resp:
            raise OSError(f"Polarity query not supported or invalid response: {resp}")

        val_str = resp.split("=")[1].strip().upper()
        if val_str.startswith("P"):
            return self.Polarity.POSITIVE
        elif val_str.startswith("N"):
            return self.Polarity.NEGATIVE
        else:
            raise ValueError(f"Unexpected polarity string in response: {resp}")

    @polarity.setter
    def polarity(self, value: Polarity):
        """
        Set the supply polarity: "POL P" or "POL N".
        E.g.: dev.polarity = KASR.Polarity.NEGATIVE  => sends "POL N".
        Only works on KAS-R series with actual hardware polarity reversing.
        """
        if not isinstance(value, self.Polarity):
            raise ValueError("Polarity must be Polarity.POSITIVE or Polarity.NEGATIVE.")

        cmd_str = f"POL {value.value}"
        self.sendcmd(cmd_str)

    # --------------------------------------------------------
    # 6) Status / errors
    # --------------------------------------------------------
    def read_status(self) -> str:
        """
        Reads the supply status using “STS” command.
        Returns the raw string, e.g. "#1 CO LO" or "#1 CF RM" plus any error codes.
        """
        resp = self.query("STS")
        # e.g. "#1 CO LO" => means unit#1, CO => output enabled, LO => local mode
        # or "#1 CF RM" => output disabled, remote mode, etc.
        return resp

    @property
    def errors(self) -> str:
        """
        Returns any error messages gleaned from STS if the supply is in error state.
        The manual says: “In the error status, all errors that occurred will be returned.”
        If no error, we might see just "#1 CO LO" or "#1 CF RM" etc.
        """
        stat = self.read_status()
        # If there's an error, it might appear after #1 ...
        # For example the manual might say you'd see "#1 CF LO E101" or something.
        # It's not very explicit. We'll just return the raw STS if it doesn't match normal.
        # We'll do a simple parse:
        normal_tokens = ["CF", "CO", "LO", "RM"]  # typical combos
        # if we see something else, we consider that an error chunk
        tokens = stat.split()
        error_tokens = [t for t in tokens if t not in ["#1", "CF", "CO", "LO", "RM"]]
        if not error_tokens:
            return "No error"
        return " ".join(error_tokens)

    # --------------------------------------------------------
    # 7) Remote / local
    # --------------------------------------------------------
    def enter_remote_mode(self):
        """
        Send "REN" to put the supply in remote mode.
        """
        self.sendcmd("REN")

    def enter_local_mode(self):
        """
        Send "GTL" to put the supply in local mode.
        """
        self.sendcmd("GTL")


    # --------------------------------------------------------
    # 8) Unit number
    # --------------------------------------------------------
    @property
    def unit_number(self) -> int:
        """
        Query the “UNIT?” to see which unit number is set. Usually 0 or 1.
        """
        resp = self.query("UNIT?")
        # doc says in response to "UNIT?", returns e.g. "UNIT=0"
        if "=" in resp:
            val_str = resp.split("=")[1]
            return int(val_str)
        return 0

    @unit_number.setter
    def unit_number(self, val: int):
        """
        Send "UNIT x" to set the device's unit number (0..31).
        """
        if not (0 <= val <= 31):
            raise ValueError("Unit number must be 0..31.")
        self.sendcmd(f"UNIT {val}")

    # --------------------------------------------------------
    # 9) Our "software" current limit
    # --------------------------------------------------------
    @property
    def current_limit(self) -> float:
        """
        A purely software-stored current limit (in mA).
        The hardware does not have an ISET command, so we store it here in Python.
        """
        return self._current_limit

    @current_limit.setter
    def current_limit(self, value: float):
        """
        Just store internally, no command is sent.
        The application code can check `if current_real > current_limit: ...`
        """
        if value < 0:
            raise ValueError("current_limit must be positive.")
        self._current_limit = value

    # --------------------------------------------------------
    # 10) Utility methods
    # --------------------------------------------------------
    def sendcmd(self, cmd: str):
        """
        Send a command that does *not* necessarily return a response.
        """
        # For Matsu. doc says commands are "OUT ON", "VSET 12.34", etc.
        # Typically we end with CR.  So:
        to_send = cmd + "\r"
        super().sendcmd(to_send)

    def query(self, cmd: str) -> str:
        """
        Send a command that *does* return a response. e.g. "VGET", "STS", ...
        We'll read until terminator.
        """
        to_send = cmd + "\r"
        try:
            super().sendcmd(to_send)
            response = self.read().strip()
            return response
        except TimeoutError as e:
            raise OSError(f"Matsusada HV timed out while querying: {cmd}. Original error: {e}")
        except Exception as e:
            raise OSError(f"Matsusada HV communication error for cmd {cmd}: {e}")


