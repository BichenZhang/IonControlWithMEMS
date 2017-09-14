# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************

import logging
import struct

from pulser.PulserHardwareClient import check
from modules.quantity import Q
from modules.Expression import Expression
from pulser.Encodings import encode, decode
from pulser.PulserConfig import DAADInfo
from gui.ExpressionValue import ExpressionValue
from modules.descriptor import SetterProperty


class MemsPositionsException(Exception):
    pass


class MemsPositionsSetting(object):
    expression = Expression()
    def __init__(self, globalDict=None ):
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
        return self._voltage.value

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


class MemsPositions:
    memsPositionsSetting = MemsPositionsSetting

    def __init__(self, pulser):
        self.commandBuffer = list()
        self.autoFlush = True
        self.pulser = pulser
        config = self.pulser.pulserConfiguration()
        self.numIons = config.ions.numChannels if config else 0
        self.ionInfo = config.ions if config else DAADInfo()

    def setVoltage(self, channel, voltage):
        intVoltage = encode(voltage, 'MEMS_VOLTAGE')
        return intVoltage

if __name__ == "__main__":
    ad = MemsPositions(None)
