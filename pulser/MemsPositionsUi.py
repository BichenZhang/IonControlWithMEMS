# *****************************************************************
# IonControl:  Copyright 2016 Sandia Corporation
# This Software is released under the GPL license detailed
# in the file "license.txt" in the top-level IonControl directory
# *****************************************************************
from PyQt5 import QtGui
from PyQt5 import QtWidgets

import PyQt5.uic

from externalParameter.persistence import DBPersist
from externalParameter.decimation import StaticDecimation
from modules.quantity import is_Q, Q
from functools import partial
import time
from collections import defaultdict
from modules.Expression import Expression
from .MemsPositionsTableModel import MemsPositionsTableModel
from uiModules.MagnitudeSpinBoxDelegate import MagnitudeSpinBoxDelegate
from modules.GuiAppearance import restoreGuiState, saveGuiState 
import logging
import traceback
from modules.Utility import unique
from pulser.PulserConfig import DAADInfo
from pulser.MemsPositions import MemsPositions

import os
uipath = os.path.join(os.path.dirname(__file__), '..', 'ui/MemsPositions.ui')
MemsPositionsForm, MemsPositionsBase = PyQt5.uic.loadUiType(uipath)

def extendTo(array, length, defaulttype):
    for _ in range(len(array), length):
        array.append(defaulttype())
        
        
class MemsPositionSettings(object):
    expression = Expression()
    def __init__(self):
        self.x1 = Q(0, 'V')
        self.x1c = Q(0, 'V')
        self.y1 = Q(0, 'V')
        self.y1c = Q(0, 'V')
        self.x2 = Q(0, 'V')
        self.x2c = Q(0, 'V')
        self.y2 = Q(0, 'V')
        self.y2c = Q(0, 'V')
        self.x1Text = '0 V'
        self.x1cText = '0 V'
        self.y1Text = '0 V'
        print ('decide on one of these inits for the text')
        self.y1cText = None
        self.x2Text = None
        self.x2cText = None
        self.y2Text = None
        self.y2cText = None

        self.ion = None #was channel
        
    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('ion', None)

class Settings:
    pass

class MemsPositionsUi(MemsPositionsForm, MemsPositionsBase):
    def __init__(self, pulser, config, configName='MemsPositionsUi', globalDict=dict(), globalVariablesModel=None, parent=None):
        self.isSetup = False
        self.persistSpace = 'MEMSPositions'
        MemsPositionsBase.__init__(self, parent)
        MemsPositionsForm.__init__(self)

        self.config = config
        self.configname = configName
        self.memsPositions = MemsPositions(pulser)
        self.settings = self.config.get(configName, Settings())
        self.channelsConfigName = '{0}.memsPositionsExpressionConfigName'.format(configName)
        self.guiStateConfigName = '{0}.guiState'.format(configName)
        self.memsPositionsChannels = self.config.get(self.channelsConfigName)
        #self.memsPositionsChannels = None #enable for debugging
        if not self.memsPositionsChannels or len(self.memsPositionsChannels) != self.memsPositions.numIons:
            self.memsPositionsChannels = [MemsPositions.memsPositionsSetting(globalDict=globalDict) for _ in range(self.memsPositions.numIons)]

        for index, channel in enumerate(self.memsPositionsChannels):
            channel.globalDict = globalDict
            channel.onx1Change = partial(self.onx1Change, index)
            channel.onx1cChange = partial(self.onx1cChange, index)
            channel.ony1Change = partial(self.ony1Change, index)
            channel.ony1cChange = partial(self.ony1cChange, index)
            channel.onx2Change = partial(self.onx2Change, index)
            channel.onx2cChange = partial(self.onx2cChange, index)
            channel.ony2Change = partial(self.ony2Change, index)
            channel.ony2cChange = partial(self.ony2cChange, index)

        self.decimation = defaultdict(lambda: StaticDecimation(Q(30, 's')))
        self.persistence = DBPersist()
        self.globalDict = globalDict
        self.pulser = pulser
        self.n = 0

        # Set up the global variables we need for storing the combined voltage values for the ppp program
        self.globalVariablesModel = globalVariablesModel
        for j in range(0, self.memsPositions.numIons):
            self.globalVariablesModel.addVariable(('memsVoltagesIon'+str(j+1)), 'Reserved MEMS')


    def setupUi(self, parent):
        self.isSetup = True
        MemsPositionsForm.setupUi(self, parent)
        self.MemsPositionsTableModel = MemsPositionsTableModel(self.memsPositionsChannels, self.globalDict)
        self.tableView.setModel(self.MemsPositionsTableModel)
        self.delegate1 = MagnitudeSpinBoxDelegate(self.globalDict)
        self.delegate2 = MagnitudeSpinBoxDelegate(self.globalDict)
        self.delegate3 = MagnitudeSpinBoxDelegate(self.globalDict)
        self.delegate4 = MagnitudeSpinBoxDelegate(self.globalDict)
        self.delegate5 = MagnitudeSpinBoxDelegate(self.globalDict)
        self.delegate6 = MagnitudeSpinBoxDelegate(self.globalDict)
        self.delegate7 = MagnitudeSpinBoxDelegate(self.globalDict)
        self.delegate8 = MagnitudeSpinBoxDelegate(self.globalDict)
        #self.tableView.setItemDelegateForColumn(0, self.delegate)
        self.tableView.setItemDelegateForColumn(1, self.delegate1)
        self.tableView.setItemDelegateForColumn(2, self.delegate2)
        self.tableView.setItemDelegateForColumn(3, self.delegate3)
        self.tableView.setItemDelegateForColumn(4, self.delegate4)
        self.tableView.setItemDelegateForColumn(5, self.delegate5)
        self.tableView.setItemDelegateForColumn(6, self.delegate6)
        self.tableView.setItemDelegateForColumn(7, self.delegate7)
        self.tableView.setItemDelegateForColumn(8, self.delegate8)
        self.tableView.verticalHeader().hide()

        self.accepted.connect(self.onClose)
        self.rejected.connect(self.onClose)

        if hasattr(self.settings, 'state'):
            self.restoreState( self.settings.state )
        restoreGuiState(self, self.config.get(self.guiStateConfigName))

        self.updateGlobalCombinedVoltages()

    def onx1Change(self, index, name, value, string, origin ):
        # index here is ion or row
        if self.isSetup and origin != 'value':
            self.MemsPositionsTableModel.setVoltage(self.MemsPositionsTableModel.createIndex(index, self.n+1), value)
        self.updateGlobalCombinedVoltages([index])

    def onx1cChange(self, index, name, value, string, origin ):
        if self.isSetup and origin != 'value':
            self.MemsPositionsTableModel.setVoltage(self.MemsPositionsTableModel.createIndex(index, self.n+2), value)
        traceback.print_stack()

        print("on x1c")
        print("index is " + str(index) + ' and self.n+1 is ' + str(self.n + 2))
        self.updateGlobalCombinedVoltages([index])

    def ony1Change(self, index, name, value, string, origin ):
        if self.isSetup and origin != 'value':
            self.MemsPositionsTableModel.setVoltage(self.MemsPositionsTableModel.createIndex(index, self.n+3), value)

        traceback.print_stack()

        print("on y1")
        print("index is " + str(index) + ' and self.n+1 is ' + str(self.n + 3))
        self.updateGlobalCombinedVoltages([index])

    def ony1cChange(self, index, name, value, string, origin ):
        if self.isSetup and origin != 'value':
            self.MemsPositionsTableModel.setVoltage(self.MemsPositionsTableModel.createIndex(index, self.n+4), value)
        traceback.print_stack()
        print("on y1c")
        print("index is " + str(index) + ' and self.n+1 is ' + str(self.n + 4))
        self.updateGlobalCombinedVoltages([index])

    def onx2Change(self, index, name, value, string, origin ):
        if self.isSetup and origin != 'value':
            self.MemsPositionsTableModel.setVoltage(self.MemsPositionsTableModel.createIndex(index, self.n+5), value)
        traceback.print_stack()
        print("on x2")
        print("index is " + str(index) + ' and self.n+1 is ' + str(self.n + 5))
        self.updateGlobalCombinedVoltages([index])

    def onx2cChange(self, index, name, value, string, origin ):
        if self.isSetup and origin != 'value':
            self.MemsPositionsTableModel.setVoltage(self.MemsPositionsTableModel.createIndex(index, self.n+6), value)
        traceback.print_stack()
        print("on x2c")
        print("index is " + str(index) + ' and self.n+1 is ' + str(self.n + 6))
        self.updateGlobalCombinedVoltages([index])

    def ony2Change(self, index, name, value, string, origin ):
        if self.isSetup and origin != 'value':
            self.MemsPositionsTableModel.setVoltage(self.MemsPositionsTableModel.createIndex(index, self.n+7), value)

        print("on y2")
        print("index is " + str(index) + ' and self.n+1 is ' + str(self.n + 7))
        self.updateGlobalCombinedVoltages([index])

    def ony2cChange(self, index, name, value, string, origin ):
        if self.isSetup and origin != 'value':
            self.MemsPositionsTableModel.setVoltage(self.MemsPositionsTableModel.createIndex(index, self.n+8), value)

        print("on y2c")
        print("index is " + str(index) + ' and self.n+1 is ' + str(self.n + 8))
        self.updateGlobalCombinedVoltages([index])

    def evaluate(self, name):  # used on global variable update
        for channel, settings in enumerate(self.memsPositionsChannels):
            if settings.evaluatex1(self.globalDict):
                self.memsPositions.setVoltage(channel, settings.x1)
                self.updateGlobalCombinedVoltages([channel])
            if settings.evaluatex1c(self.globalDict):
                self.memsPositions.setVoltage(channel, settings.x1c)
                self.updateGlobalCombinedVoltages([channel])
            if settings.evaluatey1(self.globalDict):
                self.memsPositions.setVoltage(channel, settings.y1)
                self.updateGlobalCombinedVoltages([channel])
            if settings.evaluatey1c(self.globalDict):
                self.memsPositions.setVoltage(channel, settings.y1c)
                self.updateGlobalCombinedVoltages([channel])
            if settings.evaluatex2(self.globalDict):
                self.memsPositions.setVoltage(channel, settings.x2)
                self.updateGlobalCombinedVoltages([channel])
            if settings.evaluatex2c(self.globalDict):
                self.memsPositions.setVoltage(channel, settings.x2c)
                self.updateGlobalCombinedVoltages([channel])
            if settings.evaluatey2(self.globalDict):
                self.memsPositions.setVoltage(channel, settings.y2)
                self.updateGlobalCombinedVoltages([channel])
            if settings.evaluatey2c(self.globalDict):
                self.memsPositions.setVoltage(channel, settings.y2c)
                self.updateGlobalCombinedVoltages([channel])
        self.tableView.viewport().repaint()

    def updateGlobalCombinedVoltages(self, rows=None):
        if rows is None:
            rows = range(0, self.memsPositions.numIons)
        for j in rows:
            try:
                ch0V = self.memsPositionsChannels[j].x1 + self.memsPositionsChannels[j].x1c
                ch1V = self.memsPositionsChannels[j].y1 + self.memsPositionsChannels[j].y1c
                ch2V = self.memsPositionsChannels[j].x2 + self.memsPositionsChannels[j].x2c
                ch3V = self.memsPositionsChannels[j].y2 + self.memsPositionsChannels[j].y2c
                ch0V = int(round(2 ** 15 * (ch0V.m_as('V') / 10)))
                ch1V = int(round(2 ** 15 * (ch1V.m_as('V') / 10)))
                ch2V = int(round(2 ** 15 * (ch2V.m_as('V') / 10)))
                ch3V = int(round(2 ** 15 * (ch3V.m_as('V') / 10)))
                self.globalVariablesModel._globalDict_[('memsVoltagesIon'+str(j+1))].value = (((ch0V << 48) | (ch1V << 32) | (ch2V << 16) | ch3V), "gui")
                print('MEMS combined voltage for ion #' + str(j+1))
                print(self.globalDict[('memsVoltagesIon'+str(j+1))])
            except ValueError as e:
                logging.getLogger(__name__).error((('MEMS ion positions units error, please check MemsPositionsUi Ion #' + str(j+1)) + " {0}").format(e))

    def persistCallback(self, source, data):
        time, value, minval, maxval = data
        unit = None
        if is_Q(value):
            value, unit = value.m, "{:~}".format(value.units)
        self.persistence.persist(self.persistSpace, source, time, value, minval, maxval, unit)

    def saveConfig(self):
        self.config[self.channelsConfigName] = self.memsPositionsChannels
        self.settings.isVisible = self.isVisible()
        self.config[self.configname] = self.settings
        self.config[self.guiStateConfigName] = saveGuiState(self)
        
    def onClose(self):
        self.saveConfig()
        # update globals
        self.updateGlobalCombinedVoltages()

    def closeEvent(self, e):
        self.onClose()

if __name__ == "__main__":
    import sys
    from persist import configshelve
    app = QtWidgets.QApplication(sys.argv)
    with configshelve.configshelve("test") as config:
        ui = MemsPositionsUi(config, None)
        ui.setupUi(ui)
        ui.show()
        sys.exit(app.exec_())
