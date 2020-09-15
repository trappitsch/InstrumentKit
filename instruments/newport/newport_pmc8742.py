#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides support for the Newport ESP-301 motor controller.

Due to the complexity of this piece of equipment, and relative lack of
documentation and following of normal SCPI guidelines, this file more than
likely contains bugs and non-complete behaviour.
"""

# IMPORTS #####################################################################

from contextlib import contextmanager
from enum import IntEnum
from functools import reduce
from time import time, sleep

from instruments.abstract_instruments import Instrument
from instruments.newport.errors import NewportError
import instruments.units as u
from instruments.util_fns import assume_units, ProxyList


class PicoMotorController8742(Instrument):

    class Channel:
        def __init__(self, parent, idx):
            if not isinstance(parent, PicoMotorController8742):
                raise TypeError("Don't do that.")

            # set controller
            self._parent = parent

    @property
    def axis(self):
        return ProxyList(self, self.Channel, range(4))

