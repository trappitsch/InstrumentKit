#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides support for the Newport Pico Motor Controller 8742

# ToDo:
Matlab script:
https://github.com/cnanders/matlab-newfocus-model-8742
-> Seems like it sends 6 bytes of header in TCP/IP mode. Same that I saw
-> Need to strip 6 header bytes in TCP/IP mode.

Same on USB, is the header also 6 bytes?

Port is 23...
"""

# IMPORTS #####################################################################

from contextlib import contextmanager
from enum import IntEnum
from functools import reduce
import time
from instruments.abstract_instruments import Instrument
from instruments.newport.errors import NewportError
import instruments.units as u
from instruments.util_fns import assume_units, ProxyList


class PicoMotorController8742(Instrument):

    def __init__(self, filelike):
        """Initialize the PicoMotorController class."""
        super(PicoMotorController8742, self).__init__(filelike)

        self._query_retries = 3

    class Channel:
        def __init__(self, parent, idx):
            """Initialize the channel with the parent and the number."""
            if not isinstance(parent, PicoMotorController8742):
                raise TypeError("Don't do that.")

            # terminator
            self.terminator = "\r"

            # set controller
            self._parent = parent
            self._idx = idx + 1  # 1 based
            self._address = None

        @property
        def address(self):
            """Get / set the address of a device as secondary.

            Valid address values are between 1 and 31.
            When setting the control value to a address, this address
            is then automatically sent along with the query command.

            If set to None, no address is sent and it is assumed that
            this controller is the primary. Internally, the controller
            value is set to 1.

            :return: Address of this device if secondary, otherwise `None`
            :rtype: int
            """
            if self._address is None:
                return None
            else:
                retval = int(self.query("SA?"))
                # set address string with return value
                self._address = f"{retval}>"

        @address.setter
        def address(self, newval):
            if newval is None:
                self._address = None
                newval = 1
            else:
                self._address = f"{newval}>"
            self.sendcmd(f"SA{newval}")

        # METHODS #

        def sendcmd(self, cmd):
            """Send a command to a channel object."""
            if self._address is None:
                self._parent.sendcmd(f"{self._idx}{cmd}")
            else:
                self._parent.sendcmd(f"{self._address}{self._idx}{cmd}")

        def query(self, cmd, size=-1):
            """Query for a channel object."""
            if self._address is None:
                return self._parent.query(f"{self._idx}{cmd}")
            else:
                return self._parent.query(f"{self._address}{self._idx}{cmd}")[len(self._address):]

    @property
    def channel(self):
        """Return a channel object."""
        return ProxyList(self, self.Channel, range(4))

    @property
    def dhcp_mode(self):
        """Get / set if device is in DHCP mode.

        If not in DHCP mode, a static IP address, gateway, and netmask
        must be set.

        :return: Status if DHCP mode is enabled
        :rtype: `bool`
        """
        return bool(self.query("IPMODE?"))

    @dhcp_mode.setter
    def dhcp_mode(self, newval):
        nn = 1 if newval else 0
        self.sendcmd(f"IPMODE {nn}")

    @property
    def gateway(self):
        """Get / set the gateway of the instrument.

        :return: Gateway address
        :rtype: `str`
        """
        return self.query("GATEWAY?")

    @gateway.setter
    def gateway(self, value):
        self.sendcmd(f"GATEWAY {value}")
        
    @property
    def hostname(self):
        """Get / set the hostname of the instrument.

        :return: Hostname
        :rtype: `str`
        """
        return self.query("HOSTNAME?")
    
    @hostname.setter
    def hostname(self, value):
        self.sendcmd(f"HOSTNAME {value}")

    @property
    def ip_address(self):
        """Get / set the IP address of the instrument.

        :return: IP address
        :rtype: `str`
        """
        return self.query("IPADDR?")

    @ip_address.setter
    def ip_address(self, value):
        self.sendcmd(f"IPADDR {value}")

    @property
    def mac_address(self):
        """Get the MAC address of the instrument.

        :return: MAC address
        :rtype: `str`
        """
        return self.query("MACADDR?")

    @property
    def netmask(self):
        """Get / set the Netmask of the instrument.

        :return: Netmask
        :rtype: `str`
        """
        return self.query("NETMASK?")

    @netmask.setter
    def netmask(self, value):
        self.sendcmd(f"NETMASK {value}")


    @property
    def query_retries(self):
        """Get / set the number of retries for query to try.

        :return: Number of retries before raising an IOError
        :rtype: `int`
        """
        return self._query_retries

    @query_retries.setter
    def query_retries(self, newval):
        self._query_retries = newval

    # METHODS #

    def query(self, cmd, size=-1):
        """Query's the device and returns ASCII string.

        The instrument sends binary data that cannot be decoded with
        the default encoding. The first 6 bytes need to be thrown away
        before decoding, since they are a basic header.

        # ToDo:
        - Think this retry business through again
        - Error checking? To be included here?
        """
        tries = 0
        while tries < self._query_retries:
            self.sendcmd(cmd)
            retval = self._file.read_raw(size=size)
            if len(retval) <= 6:
                tries += 1
                time.sleep(0.01)  # might need time for secondaries to respond
            else:
                return retval[6:].decode("utf-8")

        raise IOError("Did not receive an answer from the instrument.")



