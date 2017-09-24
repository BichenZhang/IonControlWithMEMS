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
from pulser.Encodings import encode
from pulser.PulserConfig import DAADInfo
from gui.ExpressionValue import ExpressionValue
from modules.descriptor import SetterProperty


class MemsPositionsException(Exception):
    pass


class MemsPositionsSetting(object):
    expression = Expression()
    def __init__(self, globalDict=dict() ):
        self._globalDict = globalDict
        self._x1 = ExpressionValue(None, self._globalDict)
        self._x1c = ExpressionValue(None, self._globalDict)
        self._y1 = ExpressionValue(None, self._globalDict)
        self._y1c = ExpressionValue(None, self._globalDict)
        self._x2 = ExpressionValue(None, self._globalDict)
        self._x2c = ExpressionValue(None, self._globalDict)
        self._y2 = ExpressionValue(None, self._globalDict)
        self._y2c = ExpressionValue(None, self._globalDict)
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
    def globalDict(self):
        return self._globalDict
    
    @globalDict.setter
    def globalDict(self, globalDict):
        self._globalDict = globalDict
        self._x1.globalDict = globalDict
        self._x1c.globalDict = globalDict
        self._y1.globalDict = globalDict
        self._y1c.globalDict = globalDict
        self._x2.globalDict = globalDict
        self._x2c.globalDict = globalDict
        self._y2.globalDict = globalDict
        self._y2c.globalDict = globalDict

    @property
    def x1(self):
        return self._x1.value

    @x1.setter
    def x1(self, v):
        self._x1.value = v

    @property
    def x1Text(self):
        return self._x1.string

    @x1Text.setter
    def x1Text(self, s):
        self._x1.string = s

    @property
    def x1c(self):
        return self._x1c.value

    @x1c.setter
    def x1c(self, v):
        self._x1c.value = v

    @property
    def x1cText(self):
        return self._x1c.string

    @x1cText.setter
    def x1cText(self, s):
        self._x1c.string = s

    @property
    def y1(self):
        return self._y1.value

    @y1.setter
    def y1(self, v):
        self._y1.value = v

    @property
    def y1Text(self):
        return self._y1.string

    @y1Text.setter
    def y1Text(self, s):
        self._y1.string = s

    @property
    def y1c(self):
        return self._y1c.value

    @y1c.setter
    def y1c(self, v):
        self._y1c.value = v

    @property
    def y1cText(self):
        return self._y1c.string

    @y1cText.setter
    def y1cText(self, s):
        self._y1c.string = s

    @property
    def x2(self):
        return self._x2.value

    @x2.setter
    def x2(self, v):
        self._x2.value = v

    @property
    def x2Text(self):
        return self._x2.string

    @x2Text.setter
    def x2Text(self, s):
        self._x2.string = s

    @property
    def x2c(self):
        return self._x2c.value

    @x2c.setter
    def x2c(self, v):
        self._x2c.value = v

    @property
    def x2cText(self):
        return self._x2c.string

    @x2cText.setter
    def x2cText(self, s):
        self._x2c.string = s

    @property
    def y2(self):
        return self._y2.value

    @y2.setter
    def y2(self, v):
        self._y2.value = v

    @property
    def y2Text(self):
        return self._y2.string

    @y2Text.setter
    def y2Text(self, s):
        self._y2.string = s

    @property
    def y2c(self):
        return self._y2c.value

    @y2c.setter
    def y2c(self, v):
        self._y2c.value = v

    @property
    def y2cText(self):
        return self._y2c.string

    @y2cText.setter
    def y2cText(self, s):
        self._y2c.string = s
        
    @SetterProperty
    def onx1Change(self, onx1Change):
        self._x1.valueChanged.connect(onx1Change)

    @SetterProperty
    def onx1cChange(self, onx1cChange):
        self._x1c.valueChanged.connect(onx1cChange)

    @SetterProperty
    def ony1Change(self, ony1Change):
        self._y1.valueChanged.connect(ony1Change)

    @SetterProperty
    def ony1cChange(self, ony1cChange):
        self._y1c.valueChanged.connect(ony1cChange)

    @SetterProperty
    def onx2Change(self, onx2Change):
        self._x2.valueChanged.connect(onx2Change)

    @SetterProperty
    def onx2cChange(self, onx2cChange):
        self._x2c.valueChanged.connect(onx2cChange)

    @SetterProperty
    def ony2Change(self, ony2Change):
        self._y2.valueChanged.connect(ony2Change)

    @SetterProperty
    def ony2cChange(self, ony2cChange):
        self._y2c.valueChanged.connect(ony2cChange)

    def evaluatex1(self, globalDict):
        if self.x1Text:
            newx1 = self.expression.evaluateAsMagnitude(self.x1Text, globalDict)
            if newx1 != self.x1:
                self.x1 = newx1
        return False

    def evaluatex1c(self, globalDict):
        if self.x1cText:
            newx1c = self.expression.evaluateAsMagnitude(self.x1cText, globalDict)
            if newx1c != self.x1c:
                self.x1c = newx1c
                return True
        return False

    def evaluatey1(self, globalDict):
        if self.y1Text:
            newy1 = self.expression.evaluateAsMagnitude(self.y1Text, globalDict)
            if newy1 != self.y1:
                self.y1 = newy1
                return True
        return False

    def evaluatey1c(self, globalDict):
        if self.y1cText:
            newy1c = self.expression.evaluateAsMagnitude(self.y1cText, globalDict)
            if newy1c != self.y1c:
                self.y1c = newy1c
                return True
        return False

    def evaluatex2(self, globalDict):
        if self.x2Text:
            newx2 = self.expression.evaluateAsMagnitude(self.x2Text, globalDict)
            if newx2 != self.x2:
                self.x2 = newx2
                return True
        return False

    def evaluatex2c(self, globalDict):
        if self.x2cText:
            newx2c = self.expression.evaluateAsMagnitude(self.x2cText, globalDict)
            if newx2c != self.x2c:
                self.x2c = newx2c
                return True
        return False

    def evaluatey2(self, globalDict):
        if self.y2Text:
            newy2 = self.expression.evaluateAsMagnitude(self.y2Text, globalDict)
            if newy2 != self.y2:
                self.y2 = newy2
                return True
        return False

    def evaluatey2c(self, globalDict):
        if self.y2cText:
            newy2c = self.expression.evaluateAsMagnitude(self.y2cText, globalDict)
            if newy2c != self.y2c:
                self.y2c = newy2c
                return True
        return False

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
