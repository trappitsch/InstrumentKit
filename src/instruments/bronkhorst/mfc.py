#!/usr/bin/env python
"""Support for Bronkhorst mass flow controllers (flow meters)
Tested devices :
  -F-201CV-xxxx
"""

# IMPORTS #####################################################################
# commenter
from enum import IntEnum
from typing import Union
from time import sleep

import struct

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
        >>> ip = '10.27.16.74'
        >>> remote_port = 4001
        >>> mfctest = ik.bronkhorst.MFC.open_tcpip(ip, remote_port)
        >>> mfctest.name
        'M23206772A'
        >>> test.fsetpoint = 10 # set fsetpoint
    """

    def __init__(self, filelike, auth=None):
        # filelike : open_serial method etc. the user doesn't instantiate MFC class, he calls its open_Serial method
        # initializing class requires an open serial port, that is in filelike
        # open_serial (or open_usb or open_...) returns a class correctly initialized
        super().__init__(filelike)
        # commands definition
        self._read_commands = {
            "Serial number": ":0780047163716300\r\n",
            "Temperature": ":06800421472147\r\n",
            "Control Mode": ":06800401040104\r\n",
            "Fsetpoint": ":06800421412143\r\n",
            "Capacity unit": ":078004017F017F07\r\n",
            "Counter unit": ":0780046867686704\r\n",
            "Counter unit index": ":06800468026802\r\n",
            "IO status": ":068004720B720B\r\n",
            "Alarm info": ":06800401140114\r\n",
        }
        # Write commands expect a status
        self._write_commands = {
            "Control Mode": "80010104",
            "Fsetpoint": "80012143",
            "Capacity unit": "8001017F6D6C6E2F68\r\n",
            "Counter unit index": "80016802",
            "Counter unit": "8001686704",
        }
        self._data_type = {
            "character": 0x00,
            "integer": 0x20,
            "float": 0x40,
            "long": 0x40,
            "string": 0x60,
        }
        # units as returned by register capacity unit, conversion to defined units
        self._units = {
            "mln/min": u.mlnpmin,
            "sccm": u.sccm,
        }

        self.auth = auth
        # error codes man p.13
        self._error_codes = {
            ":0101\r\n": "General error",
            ":0102\r\n": "General error",
            ":0103\r\n": "Propar protocol error",
            ":0104\r\n": "Propar protocol error (or CRC error)",
            ":0105\r\n": "Destination node address rejected",
            ":0108\r\n": "General error",
            ":0109\r\n": "Response message timeout",
        }
        # status codes man p. 17
        self._status_codes = {
            "00": "No error",
            "01": "Process claimed",
            "02": "Command error",
            "03": "Process error",
            "04": "Parameter error",
            "05": "Parameter type error",
            "06": "Parameter value error",
            "07": "Network not active",
            "08": "Time-out start charachter",
            "09": "Time-out serial line",
            "0A": "Hardware memory error",
            "0B": "Node number error",
            "0C": "General communication error",
            "0D": "Read only parameter.",
            "0E": "Error PC-communication",
            "0F": "No RS232 connection",
            "10": "PC out of memory",
            "11": "Write only parameter",
            "12": "System configuration unknown",
            "13": "No free node address",
            "14": "Wrong interface type",
            "15": "Error serial port connection",
            "16": "Error opening communication",
            "17": "Communication error",
            "18": "Error interface bus master",
            "19": "Timeout answer",
            "1A": "No start character",
            "1B": "Error first digit",
            "1C": "Buffer overflow in host",
            "1D": "Buffer overflow",
            "1E": "No answer found",
            "1F": "Error closing communication",
            "20": "Synchronisation error",
            "21": "Send error",
            "22": "Protocol error",
            "23": "Buffer overflow in module",
        }

    @property
    def name(self) -> str:
        """Get the serial number of the instrument."""

        data = self.query(self._read_commands.get("Serial number"))
        data = self._extract_data(data)

        return bytearray.fromhex(data).decode()

    @property
    def temperature(self) -> u.Quantity:
        """Get the temperature measured by the MFC.
        :return: temperature.
        :rtype: Quantity
        """

        data = self.query(self._read_commands.get("Temperature"))
        data = self._extract_data(data)
        temperature = struct.unpack("!f", bytes.fromhex(data))[0]

        return assume_units(temperature, u.degC)

    @property
    def fsetpoint(self) -> u.Quantity:
        """Get the setpoint as a float in the capacity in which the instrument was calibrated.
        :return: fsetpoint
        :rtype: Quantity
        """

        data = self.query(self._read_commands.get("Fsetpoint"))
        print("data raw : ", data)
        data = self._extract_data(data)
        print(data)
        setpoint = struct.unpack("!f", bytes.fromhex(data))[0]
        # call capacity_unit to get the set unit
        # todo complete dictionary of units
        return assume_units(setpoint, self.capacity_unit)

    @fsetpoint.setter
    def fsetpoint(self, value):
        # u.Quantity) -> None:
        value = assume_units(value, self.capacity_unit)
        # todo set minmax depending on device
        if value < 0:
            # * self.capacity_unit:
            value = 0
            # * self.capacity_unit
        value = float(value.magnitude)
        self.sendcmd(self._make_pkg(self._write_commands.get("Fsetpoint"), value))
        # read buffer and check status :
        # check dressler cesar 1312
        # todo error if reading setpoint back is very different
        rep = self.query(self._read_commands.get("Fsetpoint"))

    # todo return type ?
    @property
    def capacity_unit(self):
        """
        Get the unit of the flow measurement and setpoint,
        return it as a unit
        """
        data = self.query(self._read_commands.get("Capacity unit"))
        print("capacity unit command : ", self._read_commands.get("Capacity unit"))
        print("capacity unit rawdata : ", data)
        data = self._extract_data(data)
        unit_str = bytearray.fromhex(data).decode()
        return self._units.get(unit_str)

    @property
    def counter_unit(self):
        """Get counter unit"""
        data = self.query(self._read_commands.get("Counter unit"))
        print("counter unit rawdata : ", data)
        data = self._extract_data(data)
        unit_str = bytearray.fromhex(data).decode()
        print("counter unit : ", unit_str)
        return unit_str

    @counter_unit.setter
    def counter_unit(self, counter_unit):
        self.sendcmd(
            self._make_pkg(self._write_commands.get("Counter unit"), counter_unit)
        )
        # read buffer and check status :
        # check dressler cesar 1312
        # todo error if reading counter unit back is very different
        rep = self.query(self._read_commands.get("Counter unit"))

    @property
    def counter_unit_index(self):
        """Get counter unit index"""
        data = self.query(self._read_commands.get("Counter unit index"))
        print("counter unit index rawdata : ", data)
        data = self._extract_data(data)
        unit_str = bytearray.fromhex(data).decode()
        print("counter unit : ", unit_str)
        return unit_str

    @counter_unit_index.setter
    def counter_unit_index(self, counter_unit_index):
        self.sendcmd(
            self._make_pkg(
                self._write_commands.get("Counter unit index"), counter_unit_index
            )
        )
        # read buffer and check status :
        # check dressler cesar 1312
        # todo error if reading counter unit back is very different
        rep = self.query(self._read_commands.get("Counter unit index"))

    @property
    def io_status(self):
        """
        Get all bits of IOstatus.
        """
        data = self.query(self._read_commands.get("IO status"))
        data = self._extract_data(data)
        print(data)
        data = int(data, 16)
        iostatus = [
            "true = read special purpose jumper",
            "not used",
            "true = read analog mode jumper",
            "true = read micro switch",
            "special purpose jumper off/on",
            "internal initialization jumper off/on",
            "analog mode jumper off/on",
            "micro switch off/on",
        ]
        b0 = data & 0b00000001
        b1 = (data & 0b00000010) >> 1
        b2 = (data & 0b00000100) >> 2
        b3 = (data & 0b00001000) >> 3
        b4 = (data & 0b00010000) >> 4
        b5 = (data & 0b00100000) >> 5
        b6 = (data & 0b01000000) >> 6
        b7 = (data & 0b10000000) >> 7
        data = list(zip([b0, b1, b2, b3, b4, b5, b6, b7], iostatus))

        return data

    @property
    def alarm_info(self):
        """
        Get bits from alarm info register
        """
        data = self.query(self._read_commands.get("Alarm info"))
        data = self._extract_data(data)
        data = int(data, 16)
        alarm_info = [
            "Alarm register 2 contains an error",
            "Alarm register 1 contains a warning",
            "Sensor signal < minimum limit",
            "Sensor signal > maxmum limit",
            "Batch counter reached its limit",
            "Power up alarm",
            "Setpoint-measure too much difference : positive",
            "Setpoint-measure too much difference : negative",
            "Master output signal not received or slave factor out of limits",
            "Hardware alarm, check hardware",
        ]
        b0 = data & 0b00000001
        b1 = (data & 0b00000010) >> 1
        b2 = (data & 0b00000100) >> 2
        b3 = (data & 0b00001000) >> 3
        b4 = (data & 0b00010000) >> 4
        b5 = (data & 0b00100000) >> 5
        b5pos = b5 & b2
        b5neg = b5 & b3
        b6 = (data & 0b01000000) >> 6
        b7 = bool((data & 0b10000000) >> 7)
        data = list(zip([b0, b1, b2, b3, b4, b5, b5pos, b5neg, b6, b7], alarm_info))
        return data

    def _extract_data(self, data):
        """
        Extracts the raw data returned by a query, removing header and terminators.

        The data returned by a query looks like : ":1003027163004D32333230363737324100\r\n"
        The length is the first byte, 10, in hex
          so data sent after the '10' has length 16 bytes until termination characters.
        Second byte, 03, is the device adress.
          03 is the default device adress,
          08 is a generic device adress (useful for query).
        3rd byte, 02, is the cmd type (manual rs232 interface p.15)
          02 is "send parameter with destination address, no status required"
        4th and 5th byte are process and parameter numbers.
        If data is a string, byte 6 is the length of the string. if byte 6 is 0x00
          final data field before terminator should also be 0x00. (manual rs232 interface p.19)

        Data starts at 6th bytes until termination characters \r\n if it is not a string
        Data type is encoded in the parameter number on bits 5 and 6. x11xxxxx means string.
        """
        # check if data has a header, else it is corrupted
        data_extracted = "data is corrupted !"
        if len(data) > 13:
            data_length_str = data[1:3]
            # hex conversion:
            data_length = int(data_length_str, 16)
            parameter = int(data[9:11], 16)
            # test data type with a mask
            is_string = parameter & self._data_type.get(
                "string"
            ) == self._data_type.get("string")

            if is_string:
                string_length = int(data[11:13], 16)
                if string_length == 0:
                    data_extracted = data[13:-3]
                else:
                    data_extracted = data[13 : 13 + 2 * string_length]
            else:
                # for other types data starts at 6th byte, that is after 10 characters + the :, so 10
                # data stops at data[-2], because of termination characters
                data_extracted = data[11:]

        return data_extracted

    def _make_pkg(self, cmd, value):
        """
        the data sent to the device is at the end of the telegram.
        Length of the telegram is adjusted with data length.
        data is converted to HEX.
        """

        if cmd is None:
            print("no command in the index")
            return
        if isinstance(value, float):
            value_hex = hex(struct.unpack("<I", struct.pack("<f", value))[0])[2:]
        elif isinstance(value, int):
            value_hex = hex(struct.unpack("<I", struct.pack("<I", 16000))[0])[2:]
        elif isinstance(value, str):
            value_hex = self._string_to_ascii(value)
        else:
            print("error make pkg")

        print(cmd)
        print(value_hex)
        print("type val ", type(value_hex))
        pkg = "".join((cmd, value_hex, "\r\n"))

        # compute and prepend length of the command, especially for string parameters :
        length = int(len(pkg[:-2]) / 2)
        # and pad length with '0' to the left
        pkg = "".join((":", str(length).rjust(2, "0"), pkg))
        print("pkg   , ", pkg)
        return pkg

    def _unpack_status(self, data):
        if data[7:9] == "00":
            return True
        else:
            return False

    def sendcmd(self, pkg: bytes) -> None:
        """Write a command to the instrument.

        Uses the query command to check return, i.e., that everything is fine,
        but does not return data.

        :param bytes pkg: The package to send to the instrument.
        """
        data = self.query(pkg)
        if data:
            status = data[7:9]
            if status != "00":
                raise OSError(
                    f"{self._status_codes.get(status, 'Unknown status error')} (DATA={data})"
                )
        else:
            raise ValueError("No data received from the device.")

    # todo not a class function
    def _string_to_ascii(self, input):
        """
        Returns a string of ASCII hex values for an input string,
        to encode data to send to the device
        """
        return "".join([item.encode("utf-8").hex() for item in input])


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
