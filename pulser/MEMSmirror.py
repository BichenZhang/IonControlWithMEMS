# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging
import numpy as np

#from pulser.PulserHardwareClient import check
from modules.quantity import Q
from modules.Expression import Expression
from pulser.Encodings import encode, decode
from gui.ExpressionValue import ExpressionValue
from modules.descriptor import SetterProperty


class MEMSException(Exception):
    pass


class MEMSMirrorSetting(object):
    expression = Expression()

    def __init__(self, globalDict=None):
        self._globalDict = None
        self._voltage = ExpressionValue(None, self._globalDict)
        self.enabled = False
        self.name = ""
        self.resetAfterPP = False

    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('resetAfterPP', False)
        self.__dict__.setdefault('_globalDict', dict())

    def __getstate__(self):
        dictcopy = dict(self.__dict__)
        dictcopy.pop('_globalDict', None)
        return dictcopy

    @property
    def outputVoltage(self):
        return self._voltage.value if self.enabled else Q(0, 'V')

    @property
    def globalDict(self):
        return self._globalDict

    @globalDict.setter
    def globalDict(self, globalDict):
        self._globalDict = globalDict
        self._voltage.globalDict = globalDict

    @property
    def voltage(self):
        return self._voltage.value

    @voltage.setter
    def voltage(self, v):
        self._voltage.value = v

    @property
    def voltageText(self):
        return self._voltage.string

    @voltageText.setter
    def voltageText(self, s):
        self._voltage.string = s

    @SetterProperty
    def onChange(self, onChange):
        self._voltage.valueChanged.connect(onChange)


class CombineWrites:
    def __init__(self, mems):
        self.restoreValue = True
        self.mems = mems

    def __enter__(self):
        self.restoreValue = self.mems.autoFlush
        self.mems.autoFlush = False
        return self.mems

    def __exit__(self, exittype, value, traceback):
        self.mems.autoFlush = self.restoreValue
        self.mems.flush()


class MEMSmirror:
    dacChannelSetting = MEMSMirrorSetting  # for GUI (using DACUi)
    combineWrites = CombineWrites

    def __init__(self, pulser):
        self.commandBuffer = list()
        self.autoFlush = True
        self.pulser = pulser
        config = self.pulser.pulserConfiguration()
        self.numChannels = len(config.memsMirrors) if config else 0  # must be called numChannels to use DACUi
        self.memsInfo = config.memsMirrors if config else []

    def rawToMagnitude(self, raw):
        return decode(raw, 'MEMS_VOLTAGE')

    def setVoltage(self, mirror, voltage, autoApply=False, applyAll=False):
        logger = logging.getLogger(__name__)
        #intVoltage = encode(voltage, 'MEMS_VOLTAGE')
        #int(round(2 ** 48 * frequency.m_as('GHz'))) & 0xffffffffffff

        intVoltage = np.int16((round(2 ** 16 * (voltage.m_as('V')))) & 0xffff >> 1)
        cmd = (mirror + 1)  # 0 corresponds to waiting for external trigger and setting all for ppp. cmd=1-4 => mirror 0-3, latch now.
        #data = self.twos_comp(intVoltage, 16)
        channel = self.memsInfo[mirror]
        self.sendCommand(channel, cmd, intVoltage)
        logger.warning("mirror {0}".format(mirror))
        logger.warning("voltage {0}".format(intVoltage))
        logger.warning("data {0}".format(binary(data)))
        return intVoltage

    def twos_comp(self, val, bits):
        # compute the 2's complement of an int val
        if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
            val -= (1 << bits)  # compute negative value
        return val  # return positive value as is

    def flush(self):
        self.pulser.setMultipleExtendedWireIn(self.commandBuffer)
        self.commandBuffer = list()

    def sendCommand(self, channel, cmd, data):
        logger = logging.getLogger(__name__)
        if self.pulser:
            self.commandBuffer.extend([(0x12, data),
                                       (0x1e, (1 << 13) | (channel & 0xff) << 4 | (cmd & 0xf))])
            if self.autoFlush:
                self.flush()
        else:
            logger.warning("Pulser not available")

    def update(self, channelmask):
        pass

    def reset(self, mems):
        # print("numChannels = {0}".format(self.numChannels))
        # for j in range(self.numChannels):
        #     print("j = {0}".format(j))
        #     self.setVoltage(j, Q(0, 'V'))
        if self.numChannels > 0:
            with self.combineWrites(mems) as stream:
                for mirror in range(self.numChannels):
                    stream.setVoltage(mirror,  Q(0, 'V'))

if __name__ == "__main__":
    ad = MEMSmirror(None)
