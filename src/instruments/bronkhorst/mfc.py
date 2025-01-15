#!/usr/bin/env python
"""Support for Bronkhorst mass flow controllers (flow meters)
   Tested devices :
     -F-201CV-xxxx
"""

# IMPORTS #####################################################################
# commenter
from enum import IntEnum
from typing import Union

from instruments.abstract_instruments import Instrument
from instruments.units import ureg as u
from instruments.util_fns import assume_units

# CLASSES #####################################################################


class MFC(Instrument):
    """Communicate with the Bronkhorst mass flow controllers
    TODO description
    TODO example

    Example:
        >>> import instruments as ik
        >>> port = '/dev/ttyUSB0'
        >>> baud = 15200
        >>> inst = ik.comet.CitoPlus1310.open_serial(port, baud)
        >>> inst.rf  # query RF state
        False
        >>> inst.rf = True  # turn on RF
    """

    def __init__(self, filelike, auth=None):
        # filelike : open_serial method etc. the user doesn't instantiate MFC class, he calls its open_Serial method
        # initializing class requires an open serial port, that is in filelike
        # open_serial (or open_usb or open_...) returns a class correctly initialized
        super().__init__(filelike)
        self.auth = auth
        # man p.13 ?
        self._exception_codes = {
            0x01: "Unknown parameter or illegal function code",
            0x04: "Value invalid",
            0x05: "Parameter not writable",
            0x06: "Parameter not readable",
            0x07: "Stop",
            0x08: "Not allowed",
            0x09: "Wrong data type",
            0x0A: "Internal error",
            0x0B: "Value too high",
            0x0C: "Value too low",
        }
        self._commands = {
            ":0703047163716300\r\n": "Serial number",
        }

    @property
    def name(self) -> str:
        """Get the name of the instrument."""
        # decide what is the name to be the return
        # put in docstring
        data = self.query(":0703047163716300\r\n")
        data = self._extract_data(data)
        return bytearray.fromhex(data).decode()

    def _extract_data(self, data):
        """The data return by a query looks like : ":1003027163004D32333230363737324100\r\n"
        The length is the first byte, 10, in hex
          so data sent after the '10' has length 16 bytes until termination characters.
        Second byte, 03, is the device adress.
          03 is the default device adress,
          08 is a generic device adress (useful for query).
        3rd byte, 02, is the cmd type (manual rs232 interface p.15)
          02 is "send parameter with destination address, no status required"
        4th and 5th byte are process and parameter numbers.
        Data starts at 6th bytes until termination characters \r\n"""
        data_length_str = data[1:3]
        # hex conversion:
        data_length = int(data_length_str[0]) * 16 + int(data_length_str)
        # data starts at 6th byte, that is after 10 characters + the :, so 10
        # data stops at data[-2], because of termination characters
        data_extracted = data[11:]
        return data_extracted


#
#    #actually commands and settigns of the device
#    @property
#    def forward_power(self) -> u.Quantity:
#        """Get the actual forward power of the generator in W.
#
#        :return: Forward power.
#        :rtype: Quantity
#        """
#        data = self.query(self._make_pkg(8021))
#        data = int.from_bytes(data, byteorder=self._byte_order)
#        return assume_units(data, u.mW).to(u.W)
#
#    @property
#    def load_power(self) -> u.Quantity:
#        """Get the actual load power of the generator in W.
#
#        :return: Load power.
#        :rtype: Quantity
#        """
#        data = self.query(self._make_pkg(8023))
#        data = int.from_bytes(data, byteorder=self._byte_order)
#        return assume_units(data, u.mW).to(u.W)
#    #get, can use print(instrument.output_power)
#    # quantity has units
#    # mfc has a unit that can (must) be read. integrate that
#    @property
#    def output_power(self) -> u.Quantity:
#        """Get/set the set output power of the generator in W.
#
#        :return: Output power.
#        :rtype: Quantity
#        """
#        data = self.query(self._make_pkg(1206))
#        data = int.from_bytes(data, byteorder=self._byte_order)
#        return assume_units(data, u.mW).to(u.W)
#    #this param can be set with inst.output_power=123456 (units optional, assumed if nto givenassume_units)
#    @output_power.setter
#    def output_power(self, value: u.Quantity) -> None:
#        value = assume_units(value, u.W).to(u.mW)
#        if value < 1 * u.W:
#            value = 0 * u.W  # instrument can't set anything lower
#        value = int(value.magnitude)
#        self.sendcmd(self._make_pkg(1206, value))
#
#    @property
#    def reflected_power(self) -> u.Quantity:
#        """Get the actual reflected power of the generator in W.
#
#        :return: Reflected power.
#        :rtype: Quantity
#        """
#        data = self.query(self._make_pkg(8022))
#        data = int.from_bytes(data, byteorder=self._byte_order)
#        return assume_units(data, u.mW).to(u.W)
#
#    @property
#    def regulation_mode(self) -> RegulationMode:
#        """Get/set the regulation mode of the generator.
#
#        :return: Regulation mode.
#        :rtype: RegulationMode
#        """
#        data = self.query(self._make_pkg(1201))
#        return self.RegulationMode(int.from_bytes(data, byteorder=self._byte_order))
#    #value is a enum, value.value is the int corresponding to the enum
#    @regulation_mode.setter
#    def regulation_mode(self, value) -> None:
#        self.sendcmd(self._make_pkg(1201, value.value))
#
#    @property
#    def rf(self) -> bool:
#        """Get/set the RF state.
#
#        :return: The RF state.
#        :rtype: bool
#        """
#        data = self.query(self._make_pkg(8000))
#        return int.from_bytes(data, byteorder=self._byte_order) != 1
#
#    @rf.setter
#    def rf(self, value: bool) -> None:
#        data = 1 if value else 0
#        self.sendcmd(self._make_pkg(1001, data))
#
#    def sendcmd(self, pkg: bytes) -> None:
#        """Write a command to the instrument.
#
#        Uses the query command to check return, i.e., that everything is fine,
#        but does not return data.
#
#        :param bytes pkg: The package to send to the instrument.
#        """
#        self.query(pkg, write_cmd=True)
#
#    def query(self, pkg: bytes, write_cmd=False) -> Union[None, bytes]:
#        """Query instrument.
#
#        This will check if the command is accepted by the instrument and if not,
#        raise an OSError with the appropriate return code that came back.
#
#        :param bytes pkg: The package to send to the instrument.
#        :param boolwrite_cmd: If True, this is a write command and will only check
#                if received package the same as sent one.
#        """
#        self._file.write_raw(pkg)
#
#        hdr = self._file.read_raw(2)
#        fn_code = hdr[1]
#
#        if fn_code != 0x41 and fn_code != 0x42:
#            exc_code = self._file.read_raw(1)[0]
#            self._check_exception(fn_code, exc_code)
#
#        if write_cmd:
#            # read the rest, make sure the packages agree and if not raise OSError.
#            len_to_read = len(pkg) - 2
#            rest = self._file.read_raw(len_to_read)
#            pkg_return = hdr + rest
#            if pkg_return != pkg:
#                raise OSError("Received package does not match sent package.")
#            return
#
#        # so it is a query and we expect data
#        data_length = self._file.read_raw(1)
#        data = self._file.read_raw(
#            int.from_bytes(data_length, byteorder=self._byte_order)
#        )
#        #crc = self._file.read_raw(2)
#
#        #crc_exp = _crc16(hdr + data_length + data).to_bytes(
#        #    2, byteorder=self._byte_order_crc
#        #)
#
#        #if crc != crc_exp:
#        #    raise OSError("CRC-16 checksum of returned package does not match.")
#
#        return data
#
#    def _check_exception(self, fn_code: int, exc_code: int) -> None:
#        """Checks if the function code is an exception and raises an OSError if so.
#
#        :param int fn_code: The function code.
#        :param int exc_code: The exception code.
#
#        :raises OSError: If the function code is an exception.
#        """
#        if fn_code != 0x41 or fn_code != 0x42:
#            raise OSError(
#                f"Exception code: {hex(exc_code)}: {self._exception_codes.get(exc_code, 'Unknown')}"
#            )
#
#    def _make_hdr(self, fn_code: int) -> bytes:
#        """Make the header according to our init settings.
#
#        :param int fn_code: The function code to use.
#
#        :return: The header bytes.
#        :rtype: bytes
#        """
#        hdr = bytes([self._address, fn_code])
#        return hdr
#
#    def _make_pkg(self, cmd_code, data=None, data_length=4):
#        """Create a package to send to the instrument.
#
#        :param int cmd_code: The command code.
#        :param data: The data to send. If None, this is a read command. Defaults to None.
#        :param int data_length: The length of the data in bytes. Only used when writing.
#
#        :return: Properly packed data to send to the instrument.
#        :rtype: bytes
#        """
#        if data is None:
#            fn_code = 0x41
#        else:
#            fn_code = 0x42
#
#        hdr = self._make_hdr(fn_code)
#
#        cmd = cmd_code.to_bytes(length=2, byteorder=self._byte_order)
#
#        if data is not None:
#            dat = data.to_bytes(length=data_length, byteorder=self._byte_order)
#        else:
#            dat = (0x01).to_bytes(length=2, byteorder=self._byte_order)
#
#        pkg = hdr + cmd + dat
#
#        return pkg
#
#
